"""
Utility functions for Player10.

This module contains helper functions for history analysis, item filtering,
and other common operations.
"""

import uuid
from collections.abc import Iterable, Sequence

from models.item import Item

from .scoring import is_pause, subjects_of


def iter_unused_items(memory_bank: Iterable[Item], seen_item_ids: set[uuid.UUID]) -> Iterable[Item]:
	"""
	Iterate over items that haven't been used yet.

	Args:
		memory_bank: The player's memory bank
		seen_item_ids: Set of item IDs that have been seen

	Yields:
		Items that haven't been used yet
	"""
	for item in memory_bank:
		item_id = getattr(item, 'id', None)
		if item_id is not None and item_id in seen_item_ids:
			continue
		yield item


def last_was_pause(history: Sequence[Item | None]) -> bool:
	"""
	Check if the last item in history was a pause.
	"""
	return len(history) > 0 and is_pause(history[-1])


def trailing_pause_count(history: Sequence[Item | None]) -> int:
	"""
	Count consecutive pauses at the end of history.
	"""
	count = 0
	for i in range(len(history) - 1, -1, -1):
		if is_pause(history[i]):
			count += 1
		else:
			break
	return count


def subjects_in_last_n_nonpause_before_index(
	history: Sequence[Item | None], idx: int, n: int
) -> set[int]:
	"""
	Get subjects from the last n non-pause items before the given index.

	Args:
		history: The conversation history
		idx: The index to look back from
		n: Number of non-pause items to look back

	Returns:
		Set of subjects from the last n non-pause items
	"""
	subjects = set()
	count = 0

	for j in range(idx - 1, -1, -1):
		if is_pause(history[j]):
			continue
		subjects.update(subjects_of(history[j]))
		count += 1
		if count >= n:
			break

	return subjects


def refresh_seen_ids(history: Sequence[Item | None], seen_item_ids: set[uuid.UUID]) -> None:
	"""
	Update the set of seen item IDs from the history.

	Args:
		history: The conversation history
		seen_item_ids: Set to update with seen item IDs
	"""
	for item in history:
		if is_pause(item):
			continue
		item_id = getattr(item, 'id', None)
		if item_id is not None:
			seen_item_ids.add(item_id)


def get_contribution_counts(history: Sequence[Item | None]) -> dict[uuid.UUID, int]:
	"""
	Get contribution counts by player ID from history.

	Args:
		history: The conversation history

	Returns:
		Dictionary mapping player_id to contribution count
	"""
	counts = {}
	for item in history:
		if is_pause(item):
			continue
		player_id = getattr(item, 'player_id', None)
		if player_id is not None:
			counts[player_id] = counts.get(player_id, 0) + 1
	return counts


def get_current_speaker(history: Sequence[Item | None]) -> uuid.UUID | None:
	"""
	Get the current speaker (player_id of the last non-pause item).

	Args:
		history: The conversation history

	Returns:
		Player ID of current speaker, or None if no speaker
	"""
	for item in reversed(history):
		if is_pause(item):
			continue
		return getattr(item, 'player_id', None)
	return None


def find_first_proposer_tier(
	counts_by_pid: dict[uuid.UUID, int], exclude_self: uuid.UUID
) -> list[uuid.UUID]:
	"""
	Find the first proposer tier (players with minimum contribution count).

	Args:
		counts_by_pid: Contribution counts by player ID
		exclude_self: Player ID to exclude from the tier

	Returns:
		List of player IDs in the first proposer tier
	"""
	if not counts_by_pid:
		return []

	# Find minimum count
	min_count = min(counts_by_pid.values())

	# Get all players with minimum count, excluding self
	tier = [
		pid for pid, count in counts_by_pid.items() if count == min_count and pid != exclude_self
	]

	return tier


def calculate_selection_weights(
	history: Sequence[Item | None], exclude_self: uuid.UUID
) -> dict[uuid.UUID, float]:
	"""
	Calculate selection weights for all players using spec-faithful logic.

	Args:
		history: The conversation history
		exclude_self: Player ID to exclude from weights

	Returns:
		Dictionary mapping player_id to selection weight
	"""
	weights = {}
	counts_by_pid = get_contribution_counts(history)
	current_speaker = get_current_speaker(history)

	# Step 1: Current speaker edge
	if current_speaker is not None and current_speaker != exclude_self:
		weights[current_speaker] = 0.5
		p_fair = 0.5
	else:
		p_fair = 1.0

	# Step 2: First proposer tier
	first_tier = find_first_proposer_tier(counts_by_pid, exclude_self)

	if first_tier:
		# Distribute fairness probability uniformly within the tier
		weight_per_player = p_fair / len(first_tier)
		for pid in first_tier:
			weights[pid] = weights.get(pid, 0.0) + weight_per_player

	return weights


def pick_safe_keepalive_item(
	memory_bank: Iterable[Item], seen_item_ids: set[uuid.UUID], history: Sequence[Item | None]
) -> Item | None:
	"""
	Pick a safe item to avoid triggering monotony penalty when keepalive is needed.

	Args:
		memory_bank: The player's memory bank
		seen_item_ids: Set of seen item IDs
		history: The conversation history

	Returns:
		A safe item to propose, or None if none available
	"""
	# Get last three non-pause items
	last_three_subject_sets = []
	i = len(history) - 1

	# Skip trailing pauses
	while i >= 0 and is_pause(history[i]):
		i -= 1

	# Get last three non-pause items
	count = 0
	while i >= 0 and count < 3:
		if not is_pause(history[i]):
			last_three_subject_sets.append(set(subjects_of(history[i])))
			count += 1
		i -= 1

	def triggers_streak_penalty(candidate: Item) -> bool:
		"""Check if a candidate would trigger monotony penalty."""
		if len(last_three_subject_sets) < 3:
			return False

		cand_subs = set(subjects_of(candidate))
		if not cand_subs:
			return False

		# Check if any subject appears in all three previous items
		intersection = (
			set.intersection(*last_three_subject_sets) if last_three_subject_sets else set()
		)
		return any(s in intersection for s in cand_subs)

	# Find best item (avoiding penalty, then by importance)
	best_item = None
	best_key = None  # (penalty_ok (1/0), importance)

	for item in iter_unused_items(memory_bank, seen_item_ids):
		penalty = triggers_streak_penalty(item)
		importance = float(getattr(item, 'importance', 0.0))
		key = (0 if penalty else 1, importance)

		if best_key is None or key > best_key:
			best_item = item
			best_key = key

	return best_item
