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

	# -------- public API --------
	def propose_item(self, history: list[Item]) -> Item | None:
		# Update repeats cache
		self._refresh_seen_ids(history)

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

		for item in self.memory_bank:
			if self._is_repeated(item, history):
				continue
			impact = self._calculate_turn_score_impact(item, history)
			score = impact['total']
			if score > best_score:
				best_score = score
				best_item = item

		return best_item if best_score >= 0 else None

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
