from collections import Counter

from models.player import GameContext, Item, Player, PlayerSnapshot


class Player4(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)
		self.ctx = ctx

	@staticmethod
	def _is_pause(x: Item | None) -> bool:
		return x is None

	@staticmethod
	def _subjects_in(items: list[Item]) -> Counter[int]:
		c = Counter()
		for it in items:
			c.update(it.subjects)
		return c

	@staticmethod
	def _take_preceding_block(history: list[Item | None], k: int) -> list[Item]:
		"""Take up to k preceding *non-pause* items, stopping if a pause is hit."""
		out: list[Item] = []
		for x in reversed(history):
			if x is None:
				break
			out.append(x)
			if len(out) == k:
				break
		out.reverse()
		return out

	@staticmethod
	def _take_window_before_pause(history: list[Item | None], k: int) -> list[Item]:
		"""
		When history ends with a pause, take up to k items *before that pause*,
		not crossing an earlier pause.
		"""
		if not history or history[-1] is not None:
			return []
		# walk left of the trailing pause
		out: list[Item] = []
		# count = 0
		for count, x in enumerate(reversed(history[:-1])):
			if x is None:
				break
			out.append(x)
			if count + 1 == k:
				break
		out.reverse()
		return out

	def _preference_bonus(self, item: Item) -> float:
		"""
		Average of (1 - k/|S|) over the item's subjects, where k is 1-based rank
		in self.preferences (a permutation of all subjects). Unknown subjects -> 0.
		Only called when history ends with a pause.
		"""
		S = len(self.preferences)
		if S == 0 or not item.subjects:
			return 0.0

		def subj_bonus(s: int) -> float:
			# worst-case (unknown) -> k = S -> 1 - S/S = 0
			k = self.preferences.index(s) + 1 if s in self.preferences else S
			return 1.0 - (k / S)

		bonuses = [subj_bonus(s) for s in item.subjects]
		return sum(bonuses) / len(bonuses)

	def _coherence_prev3_score(self, item: Item, history: list[Item | None]) -> float:
		"""
		Coherence over the previous up to 3 non-pause items:
			- Hot-streak penalty: if any subject in `item` appears in *each* of the last 3 -> -1.0
			- Otherwise, reward based on total matched frequency across prev-3:
				sum_match/len(item.subjects)
				sum_match >= 4  -> +1.5   (e.g., 2+2)
				sum_match == 3  -> +1.0   (e.g., 2+1)
				sum_match == 2  -> +0.5
				sum_match == 1  -> +0.25
				else            ->  0.0
		The window does not cross pauses.
		"""
		prev3 = self._take_preceding_block(history, 3)
		if not prev3 or not item.subjects:
			return 0.0

		# Hot-streak penalty (subject present in all three previous items)
		if len(prev3) == 3:
			sets = [set(it.subjects) for it in prev3]
			common_all3 = sets[0] & sets[1] & sets[2]
			if any(s in common_all3 for s in item.subjects):
				return -1.0
		"""if sum_match >= 4:
		elif sum_match == 3:
			return 1.0
		elif sum_match == 2:
			return 0.5
		elif sum_match == 1:
			return 0.25
		else:
			return 0.0"""
		# Count subject frequencies across prev-3
		counts = Counter()
		for it in prev3:
			counts.update(it.subjects)

		# Total matched frequency across candidate subjects
		sum_match = sum(counts.get(s, 0) for s in item.subjects)
		return sum_match / len(item.subjects)

	def _preference_tiebreak_key(self, item: Item) -> tuple[int, int, str]:
		"""
		Lower is better. Uses:
			1) best (lowest) index among the item's subjects in self.preferences
			2) sum of indices (to prefer items whose subjects are overall higher-ranked)
			3) id string for deterministic ordering
		Subjects not found in preferences rank after all known preferences.
		"""
		n = len(self.preferences)
		idxs = [(self.preferences.index(s) if s in self.preferences else n) for s in item.subjects]
		best = min(idxs) if idxs else n
		total = sum(idxs) if idxs else n * 2
		return (best, total, str(item.id))

	def _score_candidate(self, item: Item, history: list[Item | None]) -> float:
		score = 0.0

		# Repetition check: same item already in history?
		already_seen = any(h is not None and h.id == item.id for h in history)
		if already_seen:
			# repeated items lose one point and contribute zero coherence/importance
			score -= 1.0
			return score  # early return: zero importance & coherence after first instance

		# Importance (only if not repeated)
		score += float(item.importance)

		# Penalty: subject appeared in each of the previous 3 items?
		prev3 = self._take_preceding_block(history, 3)
		if len(prev3) == 3:
			sets = [set(it.subjects) for it in prev3]
			common_prev3 = sets[0].intersection(sets[1]).intersection(sets[2])
			if any(s in common_prev3 for s in item.subjects):
				score -= 1.0

		# Pause bonus: if most recent is a pause, and item has a subject not seen
		# in the 5 turns prior to the pause (not crossing an earlier pause) -> +1
		if history and history[-1] is None:
			window5 = self._take_window_before_pause(history, 5)
			seen = set()
			for it in window5:
				seen.update(it.subjects)

			# Count how many candidate subjects are unseen in the last 5 turns
			unseen_count = sum(1 for s in item.subjects if s not in seen)

			if unseen_count >= 2:
				score += 2.0  # two or more unseen subjects → +2
			elif unseen_count >= 1:
				score += 1.0  # exactly one unseen subject → +1

		# Coherence relative to up to 3 preceding (no following at the end)
		# Window cannot extend across a pause.
		else:
			context_items = self._take_preceding_block(history, 3)
			subj_counts = self._subjects_in(context_items)

			if item.subjects and context_items:
				# If any subject of I is never mentioned in CI -> -1
				if any(subj_counts.get(s, 0) == 0 for s in item.subjects):
					score -= 1.0
				# If all subjects in I are mentioned at least twice in CI -> +1
				elif all(subj_counts.get(s, 0) >= 2 for s in item.subjects):
					score += 1.0

		score += self._preference_bonus(item)
		score += self._coherence_prev3_score(item, history)
		return score

	# ------------ selection

	def propose_item(self, history: list[Item | None]) -> Item | None:
		"""
		Pick the memory_bank item with the maximum score under the rules.
		Tie-breaker: player preference order.
		Returns None if no items available.
		"""
		if not self.memory_bank:
			return None

		# Score all candidates
		scored: list[tuple[float, Item]] = [
			(self._score_candidate(it, history), it) for it in self.memory_bank
		]

		# Find best score
		if not scored:
			return None
		best_score = max(s for s, _ in scored)
		# print(best_score)
		# print(history)
		max_possible = 1.0 + 2.0 + 1.5  # importance + pause + coherence
		threshold = 1
		if len(history) != 0 and best_score < threshold:
			return None
           
		# All with best score
		tied = [it for s, it in scored if s == best_score]

		choice = tied[0] if len(tied) == 1 else min(tied, key=self._preference_tiebreak_key)

		# Track contribution if you care downstream
		self.contributed_items.append(choice)
		return choice
