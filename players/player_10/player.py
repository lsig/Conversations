from __future__ import annotations

import random
import uuid
from collections import Counter
from collections.abc import Iterable, Sequence

from models.item import Item
from models.player import GameContext, Player, PlayerSnapshot

# Creating a player for Group 10, working on RL agent


class Player10(Player):
	"""
	Hybrid policy:

		• Turn 0 (empty history) → Edge-case opener:
			- Prefer single-subject item (coherence-friendly for others to echo),
				break ties by highest importance, random among top ties.
			- If no single-subject items exist, pick highest-importance overall.

		• If there are already two consecutive pauses → Keepalive:
			- Propose a safe, non-repeated item to avoid a 3rd pause ending the game
				(spec: "If there are three consecutive pauses, ... ends prematurely").

		• Immediately after a pause → Freshness maximizer:
			- Choose a non-repeated item whose subjects are novel w.r.t. the last
				5 non-pause turns before the pause (spec Freshness).
			- Prefer 2-subject items with both novel (+2), then 1 novel (+1),
				tie-break by importance.

		• Otherwise → General scoring (Player10-style):
			- Score = importance + coherence + freshness + nonmonotonousness
				(individual bonus tracked but not added to total), choose the max.
			- If best score < 0, pass.

	Spec rules cited:
		- Freshness: post-pause novel subjects (+1 / +2).
		- Nonrepetition: repeats have zero importance; also incur -1 nonmonotonousness.
		- Nonmonotonousness: subject appearing in each of previous three items → -1.
		- Early termination: three consecutive pauses end the conversation.
	"""

	# -------- init --------
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		super().__init__(snapshot, ctx)
		self._seen_item_ids: set[uuid.UUID] = set()
		self._S = len(self.preferences)
		self._rank1: dict[int, int] = {subj: i + 1 for i, subj in enumerate(self.preferences)}
		self.last_scores = []

	# -------- public API --------
	def propose_item(self, history: list[Item]) -> Item | None:
		# Update repeats cache
		self._refresh_seen_ids(history)

		# Get cumulative scores so far for this player
		cumulative_scores = self.get_cumulative_score(history)

		# You can now use cumulative_scores to make informed decisions:
		# - cumulative_scores['total'] - total score so far
		# - cumulative_scores['importance'] - importance component
		# - cumulative_scores['coherence'] - coherence component
		# - cumulative_scores['freshness'] - freshness component
		# - cumulative_scores['nonmonotonousness'] - nonmonotonousness component
		# - cumulative_scores['individual'] - individual bonus for this player

		# Example: If our individual score is low, prioritize items that benefit us
		if cumulative_scores['individual'] < 0.5 and len(history) > 2:
			# Look for items that align with our preferences
			preference_items = [
				item
				for item in self._iter_unused_items()
				if any(
					s in self.preferences[:3] for s in self._subjects_of(item)
				)  # Top 3 preferences
				and not self._is_repeated(item, history)
			]
			if preference_items:
				# Pick highest importance from preference-aligned items
				return max(preference_items, key=lambda x: float(getattr(x, 'importance', 0.0)))

		# Turn 0: use opener logic only here
		if not history:
			return self._pick_first_turn_opener()

		# Keepalive if two pauses already
		if self._trailing_pause_count(history) >= 2:
			return self._pick_safe_keepalive(history)

		# Freshness mode: immediately after a pause
		if self._last_was_pause(history):
			cand = self._pick_fresh_post_pause(history)
			if cand is not None:
				return cand
			# else fall through to general scoring

		# Default: general scoring (importance + coherence + freshness + nonmonotonousness)
		return self._general_scoring_best(history)

	def get_cumulative_score(self, history: list[Item]) -> dict[str, float]:
		"""
		Calculate the cumulative score so far for each scoring component.

		Returns a dictionary with:
		- 'total': total cumulative score
		- 'importance': cumulative importance score
		- 'coherence': cumulative coherence score
		- 'freshness': cumulative freshness score
		- 'nonmonotonousness': cumulative nonmonotonousness score
		- 'individual': cumulative individual bonus for this player
		"""
		if not history:
			return {
				'total': 0.0,
				'importance': 0.0,
				'coherence': 0.0,
				'freshness': 0.0,
				'nonmonotonousness': 0.0,
				'individual': 0.0,
			}

		total_importance = 0.0
		total_coherence = 0.0
		total_freshness = 0.0
		total_nonmonotonousness = 0.0
		total_individual = 0.0
		unique_items = set()

		for i, item in enumerate(history):
			if item is None:  # Skip pauses
				continue

			is_repeated = item.id in unique_items
			unique_items.add(item.id)

			if is_repeated:
				# Repeated items only contribute to nonmonotonousness
				total_nonmonotonousness -= 1.0
			else:
				# Calculate scores for non-repeated items
				total_importance += item.importance
				total_coherence += self._calculate_coherence_score(i, item, history)
				total_freshness += self._calculate_freshness_score(i, item, history)
				total_nonmonotonousness += self._calculate_nonmonotonousness_score(
					i, item, False, history
				)

			# Calculate individual bonus
			bonuses = [
				1 - self.preferences.index(s) / len(self.preferences)
				for s in item.subjects
				if s in self.preferences
			]
			if bonuses:
				total_individual += sum(bonuses) / len(bonuses)

		total_score = total_importance + total_coherence + total_freshness + total_nonmonotonousness

		return {
			'total': total_score,
			'importance': total_importance,
			'coherence': total_coherence,
			'freshness': total_freshness,
			'nonmonotonousness': total_nonmonotonousness,
			'individual': total_individual,
		}

	# -------- Turn 0 opener --------
	def _pick_first_turn_opener(self) -> Item | None:
		# Prefer single-subject items
		single_subject = [it for it in self.memory_bank if len(self._subjects_of(it)) == 1]
		pool = single_subject if single_subject else list(self.memory_bank)
		if not pool:
			return None
		max_imp = max(float(getattr(it, 'importance', 0.0)) for it in pool)
		top = [it for it in pool if float(getattr(it, 'importance', 0.0)) == max_imp]
		return random.choice(top)

	# -------- Freshness logic (post-pause) --------
	def _pick_fresh_post_pause(self, history: Sequence[Item]) -> Item | None:
		recent_subjects = self._subjects_in_last_n_nonpause_before_index(
			history, idx=len(history) - 1, n=5
		)
		best_item: Item | None = None
		best_key: tuple[int, float] | None = None  # (novelty_count, importance)

		for item in self._iter_unused_items():
			subs = self._subjects_of(item)
			if not subs:
				continue
			novelty = sum(1 for s in subs if s not in recent_subjects)
			if novelty == 0:
				continue
			key = (novelty, float(getattr(item, 'importance', 0.0)))
			if best_key is None or key > best_key:
				best_item, best_key = item, key

		return best_item

	# -------- General scoring (Player10-style) --------
	def _general_scoring_best(self, history: list[Item]) -> Item | None:
		best_item = None
		best_score = float('-inf')

		# Get current cumulative scores for context-aware decision making
		cumulative_scores = self.get_cumulative_score(history)

		for item in self.memory_bank:
			if self._is_repeated(item, history):
				continue
			impact = self._calculate_turn_score_impact(item, history)
			score = impact['total']

			# Example RL-style scoring adjustments based on cumulative state:
			# If we're behind on individual score, boost items that help us
			if cumulative_scores['individual'] < 1.0:
				individual_bonus = impact.get('individual', 0.0)
				score += individual_bonus * 0.5  # 50% bonus for individual benefit

			# If conversation is struggling with coherence, prioritize coherence
			if cumulative_scores['coherence'] < 0 and impact.get('coherence', 0) > 0:
				score += 0.3  # Bonus for improving coherence

			# If we need freshness boost, prioritize fresh items
			if cumulative_scores['freshness'] < 1.0 and impact.get('freshness', 0) > 0:
				score += 0.2  # Bonus for adding freshness

			if score > best_score:
				best_score = score
				best_item = item

		last_score = (
			self._calculate_turn_score_impact(history[-1], history[:-1])['total']
			if len(history) > 1
			else 0
		)
		self.last_scores.append(last_score)
		avg_last_score = sum(self.last_scores) / len(self.last_scores)

		return best_item if best_score >= avg_last_score else None

	def _calculate_turn_score_impact(self, item: Item | None, history: list[Item]) -> dict:
		if item is None:
			return {'total': 0.0}

		turn_idx = len(history)
		impact: dict[str, float] = {}

		is_repeated = self._is_repeated(item, history)
		if is_repeated:
			impact['importance'] = 0.0
			impact['coherence'] = 0.0
			impact['freshness'] = 0.0
			impact['nonmonotonousness'] = self.__calculate_nonmonotonousness_score(
				turn_idx, item, repeated=True, history=history
			)
		else:
			impact['importance'] = float(getattr(item, 'importance', 0.0))
			impact['coherence'] = self.__calculate_coherence_score(turn_idx, item, history)
			impact['freshness'] = self.__calculate_freshness_score(turn_idx, item, history)
			impact['nonmonotonousness'] = self.__calculate_nonmonotonousness_score(
				turn_idx, item, repeated=False, history=history
			)

		# Track individual (not added to total here; keep consistent with your version)
		preferences = self.preferences
		bonuses = [
			1 - (preferences.index(s) / len(preferences)) for s in item.subjects if s in preferences
		]
		impact['individual'] = sum(bonuses) / len(bonuses) if bonuses else 0.0

		impact['total'] = sum(
			v
			for k, v in impact.items()
			if k in ['importance', 'coherence', 'freshness', 'nonmonotonousness']
		)
		return impact

	# -------- Scoring helpers --------
	def _calculate_freshness_score(self, i: int, current_item: Item, history: list[Item]) -> float:
		"""Calculate freshness score for a specific item."""
		if i == 0:
			return 0.0
		if i > 0 and history[i - 1] is not None:
			return 0.0

		prior_items = (item for item in history[max(0, i - 6) : i - 1] if item is not None)
		prior_subjects = {s for item in prior_items for s in item.subjects}
		novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]
		return float(len(novel_subjects))

	def _calculate_coherence_score(self, i: int, current_item: Item, history: list[Item]) -> float:
		"""Calculate coherence score for a specific item."""
		context_items = []

		# Past up to 3 (stop at pause)
		for j in range(i - 1, max(-1, i - 4), -1):
			if j < 0 or history[j] is None:
				break
			context_items.append(history[j])

		# Future side (usually empty at proposal time)
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

	def _calculate_nonmonotonousness_score(
		self, i: int, current_item: Item, repeated: bool, history: list[Item]
	) -> float:
		"""Calculate nonmonotonousness score for a specific item."""
		if repeated:
			return -1.0
		if i < 3:
			return 0.0

		last_three_items = [history[j] for j in range(i - 3, i)]
		if all(
			item is not None and any(s in item.subjects for s in current_item.subjects)
			for item in last_three_items
		):
			return -1.0
		return 0.0

	def __calculate_freshness_score(self, i: int, current_item: Item, history: list[Item]) -> float:
		# Only award freshness if previous turn was a pause
		if i == 0:
			return 0.0
		if i > 0 and i <= len(history) and not self._is_pause(history[i - 1]):
			return 0.0

		prior_items = (item for item in history[max(0, i - 6) : i - 1] if not self._is_pause(item))
		prior_subjects = {s for item in prior_items for s in item.subjects}
		novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]
		return float(len(novel_subjects))

	def __calculate_coherence_score(self, i: int, current_item: Item, history: list[Item]) -> float:
		context_items = []
		# Past up to 3 (stop at pause)
		for j in range(i - 1, max(-1, i - 4), -1):
			if j < 0 or self._is_pause(history[j]):
				break
			context_items.append(history[j])
		# (Future side included for symmetry but usually empty at proposal time)
		for j in range(i + 1, min(len(history), i + 4)):
			if self._is_pause(history[j]):
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
			return -1.0  # repeated items lose one point
		if i < 3:
			return 0.0
		last_three_items = [history[j] for j in range(i - 3, i)]
		if all(
			(it is not None)
			and (not self._is_pause(it))
			and any(s in it.subjects for s in current_item.subjects)
			for it in last_three_items
		):
			return -1.0
		return 0.0

	# -------- shared helpers --------
	def _iter_unused_items(self) -> Iterable[Item]:
		for item in self.memory_bank:
			item_id = getattr(item, 'id', None)
			if item_id is not None and item_id in self._seen_item_ids:
				continue
			yield item

	def _is_repeated(self, item: Item, history: Sequence[Item]) -> bool:
		item_id = getattr(item, 'id', None)
		if item_id is None:
			return False
		for it in history:
			if self._is_pause(it):
				continue
			if getattr(it, 'id', None) == item_id:
				return True
		return False

	@staticmethod
	def _is_pause(x: object) -> bool:
		if x is None:
			return True
		is_pause_attr = getattr(x, 'is_pause', None)
		if isinstance(is_pause_attr, bool):
			return is_pause_attr
		subs = getattr(x, 'subjects', None)
		return subs is None or len(subs) == 0

	@staticmethod
	def _subjects_of(x: Item) -> tuple[int, ...]:
		subs = getattr(x, 'subjects', ())
		return tuple(subs or ())

	def _last_was_pause(self, history: Sequence[Item]) -> bool:
		return len(history) > 0 and self._is_pause(history[-1])

	def _trailing_pause_count(self, history: Sequence[Item]) -> int:
		c = 0
		for i in range(len(history) - 1, -1, -1):
			if self._is_pause(history[i]):
				c += 1
			else:
				break
		return c

	def _subjects_in_last_n_nonpause_before_index(
		self, history: Sequence[Item], idx: int, n: int
	) -> set[int]:
		out: set[int] = set()
		count = 0
		for j in range(idx - 1, -1, -1):
			if self._is_pause(history[j]):
				continue
			out.update(self._subjects_of(history[j]))
			count += 1
			if count >= n:
				break
		return out

	def _refresh_seen_ids(self, history: Sequence[Item]) -> None:
		for it in history:
			if self._is_pause(it):
				continue
			item_id = getattr(it, 'id', None)
			if item_id is not None:
				self._seen_item_ids.add(item_id)

	def _pick_safe_keepalive(self, history: Sequence[Item]) -> Item | None:
		last_three_subject_sets: list[set[int]] = []
		i = len(history) - 1
		while i >= 0 and self._is_pause(history[i]):
			i -= 1
		k = 0
		while i >= 0 and k < 3:
			if not self._is_pause(history[i]):
				last_three_subject_sets.append(set(self._subjects_of(history[i])))
				k += 1
			i -= 1

		def triggers_streak_penalty(candidate: Item) -> bool:
			if len(last_three_subject_sets) < 3:
				return False
			cand_subs = set(self._subjects_of(candidate))
			if not cand_subs:
				return False
			intersection = (
				set.intersection(*last_three_subject_sets) if last_three_subject_sets else set()
			)
			return any(s in intersection for s in cand_subs)

		best: Item | None = None
		best_key: tuple[int, float] | None = None  # (penalty_ok (1/0), importance)

		for item in self._iter_unused_items():
			penalty = triggers_streak_penalty(item)
			key = (0 if penalty else 1, float(getattr(item, 'importance', 0.0)))
			if best_key is None or key > best_key:
				best, best_key = item, key

		return best

	# -------- RL Agent Helper Methods --------
	def get_game_state(self, history: list[Item]) -> dict:
		"""
		Get a comprehensive game state representation for RL training.

		Returns a dictionary containing:
		- cumulative_scores: Current cumulative scores
		- turn_info: Turn number, consecutive pauses, etc.
		- available_items: Information about items we can propose
		- recent_context: Recent conversation context
		"""
		cumulative_scores = self.get_cumulative_score(history)

		# Available items analysis
		available_items = []
		for item in self._iter_unused_items():
			impact = self._calculate_turn_score_impact(item, history)
			available_items.append(
				{
					'id': str(item.id),
					'importance': item.importance,
					'subjects': item.subjects,
					'predicted_impact': impact,
					'aligns_with_preferences': any(
						s in self.preferences[:3] for s in item.subjects
					),
				}
			)

		# Recent context analysis
		recent_context = {
			'last_was_pause': self._last_was_pause(history),
			'consecutive_pauses': self._trailing_pause_count(history),
			'recent_subjects': set(),
			'our_contributions': 0,
		}

		# Analyze last 5 turns
		for item in history[-5:]:
			if item is not None:
				recent_context['recent_subjects'].update(item.subjects)
				if item.player_id == self.id:
					recent_context['our_contributions'] += 1

		recent_context['recent_subjects'] = list(recent_context['recent_subjects'])

		return {
			'cumulative_scores': cumulative_scores,
			'turn_info': {
				'turn_number': len(history),
				'consecutive_pauses': self._trailing_pause_count(history),
				'is_early_game': len(history) < 3,
				'is_late_game': len(history) > self.conversation_length * 0.7,
			},
			'available_items': available_items,
			'recent_context': recent_context,
			'preferences': self.preferences,
		}
