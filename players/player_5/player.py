import random
from collections import Counter

from core.engine import Engine  # noqa: F821
from models.player import GameContext, Item, Player, PlayerSnapshot


class self_engine(Engine):
	pass


class Player5(Player):
	# Speed up players: only run through certain amount of memory bank
	MIN_CANDIDATES_COUNT = 10  # configure for small banks
	CANDIDATE_FRACTION = 0.2  # configure percentage for large banks

	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		super().__init__(snapshot, ctx)
		self.ctx = ctx
		self.conversation_length = ctx.conversation_length

		self.snapshot = snapshot

		# Sort memory bank by importance
		self.memory_bank.sort(key=lambda x: x.importance, reverse=True)
		self.best = self.memory_bank[0] if self.memory_bank else None

		# Internal state
		self.turn_length = 0
		self.last_turn_position = -1
		self.recent_history = Counter()
		self.score_engine = None
		self.preferences = snapshot.preferences

		# Track other subjects talked about: player id -> Counter(subject -> count)
		self.external_subjects = {}

		# Pausing strategy thresholds - tune later to be more dynamic
		self.pause_threshold = 0.5
		self.pause_count = 0

	def count_consecutive_pauses(self, history: list[Item]) -> int:
		"""Count number of consecutive pauses to avoid 3 in a row"""
		count = 0
		for item in reversed(history):
			if item is None:
				count += 1
			else:
				break

		return count

	def freshness_pause_bonus(self, history: list[Item]) -> bool:
		"""Check the expected bonus if we were to choose to pause for freshness"""
		if len(history) < 5:
			return False

		past_subjects = set()
		for item in history[-5:]:
			if item is not None:
				past_subjects.update(item.subjects)

		# check if we have anything new to contribue
		for item in self.memory_bank[:10]:
			new_subjects = [subject for subject in item.subjects if subject not in past_subjects]
			if len(new_subjects) >= 1:
				return True

		return False

	def monotony_pause_bonus(self, history: list[Item]) -> bool:
		"""Check the expected bonus if we were to choose to pause for monotony"""
		if len(history) < 3:
			return False

		past_subjects = []
		for item in history[-3:]:
			if item is not None:
				past_subjects.extend(item.subjects)

		subject_frequencies = Counter(past_subjects)
		# monotonoy = 3+ same subjects
		return any(count >= 3 for count in subject_frequencies.values())

	def update_external_subjects(self, history: list[Item]) -> None:
		"""Update the counter for external subjects mentioned by other players"""
		# Note down what's been said by everyone
		for item in history:
			# skip pauses
			if item is None:
				continue
			if item.player_id == self.snapshot.id:
				continue
			# exclude stuff we said
			if item not in self.external_subjects:
				self.external_subjects[item.player_id] = Counter()
			for subject in item.subjects:
				self.external_subjects[item.player_id][subject] += 1

	def predict_group_preference(self) -> Counter:
		"""Predict what subjects other external players prefer"""
		combined = Counter()
		# Combine everyone's preferences to see the group preference
		for counter in self.external_subjects.values():
			combined.update(counter)
		return combined

	def individual_score(self, item: Item) -> float:
		"""Score based on player preferences."""
		score = 0
		bonuses = [
			1 - self.preferences.index(s) / len(self.preferences)
			for s in item.subjects
			if s in self.preferences
		]
		if bonuses:
			score += sum(bonuses) / len(bonuses)
		return score

	def rrf_score(
		self,
		item: Item,
		shared_map: dict,
		pref_map: dict,
		imp_map: dict,
		turns_left: int,
	) -> float:
		"""Calculate Reciprocal Rank Fusion (RRF) score for one item."""
		k = 60
		if turns_left <= 3:
			# Lean into more important topics
			return (
				1 / (k + shared_map.get(item, len(self.memory_bank)))
				+ 2 * (1 / (k + pref_map.get(item, len(self.memory_bank))))
				+ 3 * (1 / (k + imp_map.get(item, len(self.memory_bank))))  # triple weight
			)
		else:
			return (
				1 / (k + shared_map.get(item, len(self.memory_bank)))
				+ 2
				* (1 / (k + pref_map.get(item, len(self.memory_bank))))  # weight preferences higher
				+ 1 / (k + imp_map.get(item, len(self.memory_bank)))
			)

	def propose_item(self, history: list[Item]) -> Item | None:
		if not self.memory_bank:
			return None

		# check if should pause based on freshness or monotony
		best_item = self.memory_bank[0]
		base_value = best_item.importance + self.individual_score(best_item)

		future_bonus = 0
		if self.freshness_pause_bonus(history):
			future_bonus += max(1.0, 0.5 * base_value)
		if self.monotony_pause_bonus(history):
			future_bonus += max(1.0, 0.5 * base_value)

		# calcula te exepcted current best item score
		if self.memory_bank:
			expected = self.individual_score(self.memory_bank[0]) + self.memory_bank[0].importance
		else:
			expected = 0

		# scale pause value by turns left to discourage late-game pauses
		turns_left = self.conversation_length - len(history)
		effective_pause_value = future_bonus * (turns_left / (turns_left + 5))
		# tune this value dynamically better in future
		if effective_pause_value > 0.85 * expected:
			return None

		# Note down what's been said by everyone
		self.update_external_subjects(history)
		group_subject_preference = self.predict_group_preference()

		# For now, we examine only the previously spoken player
		prev_player = None
		for item in reversed(history):
			if item is not None and item.player_id != self.snapshot.id:
				prev_player = item.player_id
				break
		prev_player_preferences = (
			self.external_subjects.get(prev_player, Counter()) if prev_player else Counter()
		)

		# Create a temporary engine for shared scoring
		self.score_engine = self_engine(
			players=[],
			player_count=0,
			subjects=0,
			memory_size=len(self.memory_bank),
			conversation_length=self.conversation_length,
			seed=0,
		)
		# FIX: snapshots must be a dict, not a list
		self.score_engine.snapshots = {self.snapshot.id: self.snapshot}

		# Build three rankings:
		shared_ranking = []
		pref_ranking = []
		importance_ranking = []
		total_ranking = []

		# speed up player: run through either the min baseline(smaller memories) or a percentage(larger ones)
		candidates = max(
			self.MIN_CANDIDATES_COUNT, int(len(self.memory_bank) * self.CANDIDATE_FRACTION)
		)
		top_candidates = self.memory_bank[:candidates]
		if not top_candidates:
			return None

		for item in top_candidates:
			new_history = history + [item]
			self.score_engine.history = new_history
			shared_score = self.score_engine._Engine__calculate_scores()
			self_score = self.individual_score(item)

			shared_score = round(shared_score['shared'], 4)
			self_score = round(self_score, 4)

			# print(
			# f'Score for {item.subjects}: {shared_score}, {self_score}, total: {round(shared_score + self_score, 4)}'
			# )

			total_ranking.append((item, shared_score + self_score))
			shared_ranking.append((item, shared_score))
			pref_ranking.append((item, self_score))
			importance_ranking.append((item, item.importance))

		# Sort each list descending (best first)

		strategy = 'greedy'

		if strategy == 'greedy':
			total_ranking.sort(key=lambda x: x[1], reverse=True)
			best_item = total_ranking[0][0]
			return best_item

		shared_ranking.sort(key=lambda x: x[1], reverse=True)
		pref_ranking.sort(key=lambda x: x[1], reverse=True)
		importance_ranking.sort(key=lambda x: x[1], reverse=True)

		# Build rank maps for quick lookup
		def build_rank_map(ranking):
			return {item: rank for rank, (item, _) in enumerate(ranking, start=1)}

		shared_map = build_rank_map(shared_ranking)
		pref_map = build_rank_map(pref_ranking)
		imp_map = build_rank_map(importance_ranking)

		# Nearing the end, maximize individual score by preferring high importance topics
		turns_left = self.conversation_length - len(history)

		# Track subject repetition
		recent_subjects = [s for item in history[-3:] for s in item.subjects]
		count_recent = Counter(recent_subjects)

		# Add freshness bonus after pause
		last_pause = max((index for index, item in enumerate(history) if item is None), default=-1)
		history_post_pause = history[last_pause + 1 :]
		subjects_post_pause = {
			subject for item in history_post_pause if item is not None for subject in item.subjects
		}

		scores = {}
		for item in self.memory_bank:
			# Base score from RRF
			scores[item] = self.rrf_score(item, shared_map, pref_map, imp_map, turns_left)

			if any(count_recent[subject] >= 3 for subject in item.subjects):
				# non-monotonous penalty
				scores[item] -= 1

			# freshness: count how many subjects of an item hasn't been mentioned since pause
			new_subject_count = sum(
				1 for subject in item.subjects if subject not in subjects_post_pause
			)
			scores[item] += new_subject_count

			# Adjust score based on the entire group's preferred subjects
			for subject in item.subjects:
				# No one else mentioned - bonus
				if group_subject_preference[subject] == 0:
					scores[item] += 0.5  # tune later
				# repeated too much
				elif group_subject_preference[subject] > 3:
					scores[item] -= 0.5  # tune later

			# Adjust score based on direct previous player
			for subject in item.subjects:
				if prev_player_preferences[subject] > 0:
					# try to be cohesive with the last player's subject preferences
					scores[item] += 1.5  # tune later

		# Pick best
		best_score = max(scores.values())
		highest_candidates = [item for item, s in scores.items() if s == best_score]
		return random.choice(highest_candidates)
