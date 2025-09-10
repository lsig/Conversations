from models.player import Item, Player, PlayerSnapshot
from collections import Counter
import uuid
import random


# Creating a player for Group 10


class Player10(Player):
	"""
	Player for Group 10
	"""

	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		"""
		Initialize the player
		"""
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		"""
		Propose an item from memory bank with maximum turn score impact
		"""

		best_item = None
		best_score = float('-inf')

		for item in self.memory_bank:
			impact = self._calculate_turn_score_impact(item, history)
			score = impact['total']

			if score > best_score:
				best_score = score
				best_item = item
		if score < 0:
			return None
		return best_item

	def __calculate_freshness_score(self, i: int, current_item: Item, history: list[Item]) -> float:
		if i == 0:
			return 0.0

		# Check if the previous item exists and is not None
		if i > 0 and i <= len(history) and history[i - 1] is not None:
			return 0.0

		prior_items = (item for item in history[max(0, i - 6) : i - 1] if item is not None)
		prior_subjects = {s for item in prior_items for s in item.subjects}

		novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]

		return float(len(novel_subjects))

	def __calculate_coherence_score(self, i: int, current_item: Item, history: list[Item]) -> float:
		context_items = []

		for j in range(i - 1, max(-1, i - 4), -1):
			if history[j] is None:
				break
			context_items.append(history[j])

		for j in range(i + 1, min(len(history), i + 4)):
			if history[j] is None:
				break
			context_items.append(history[j])

		context_subject_counts = Counter(s for item in context_items for s in item.subjects)
		score = 0.0

		if not all(subject in context_subject_counts for subject in current_item.subjects):
			score -= 1.0

		if all(context_subject_counts.get(s, 0) >= 2 for s in current_item.subjects):
			score += 1.0

		return score

	def __calculate_nonmonotonousness_score(
		self, i: int, current_item: Item, repeated: bool, history: list[Item]
	) -> float:
		if repeated:
			return -1.0

		if i < 3:
			return 0.0

		last_three_items = [history[j] for j in range(i - 3, i)]
		if all(
			item and any(s in item.subjects for s in current_item.subjects)
			for item in last_three_items
		):
			return -1.0

		return 0.0

	def _calculate_turn_score_impact(self, item: Item | None, history: list[Item]) -> dict:
		if item is None:
			return {'total': 0.0}

		# Calculate what the turn index would be if we added this item
		# If history is empty, this would be the first turn (index 0)
		# Otherwise, it would be the next turn (current length)
		turn_idx = len(history)

		impact = {}

		is_repeated = any(
			existing_item and existing_item.id == item.id for existing_item in history[:-1]
		)

		if is_repeated:
			impact['importance'] = 0.0
			impact['coherence'] = 0.0
			impact['freshness'] = 0.0
			impact['nonmonotonousness'] = self.__calculate_nonmonotonousness_score(
				turn_idx, item, repeated=True, history=history
			)
		else:
			impact['importance'] = item.importance
			impact['coherence'] = self.__calculate_coherence_score(turn_idx, item, history)
			impact['freshness'] = self.__calculate_freshness_score(turn_idx, item, history)
			impact['nonmonotonousness'] = self.__calculate_nonmonotonousness_score(
				turn_idx, item, repeated=False, history=history
			)

		# For individual bonus, we need to find the last player who spoke
		# This is a simplified approach - in practice you might need more context
		individual_bonus = 0.0
		preferences = self.preferences
		bonuses = [
			1 - preferences.index(s) / len(preferences) for s in item.subjects if s in preferences
		]
		if bonuses:
			individual_bonus = sum(bonuses) / len(bonuses)
		impact['individual'] = individual_bonus
		impact['total'] = sum(
			v
			for k, v in impact.items()
			if k in ['importance', 'coherence', 'freshness', 'nonmonotonousness']
		)

		return impact
