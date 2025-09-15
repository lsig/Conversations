from collections import Counter
import random

from core.engine import Engine  # noqa: F821
from models.player import GameContext, Item, Player, PlayerSnapshot


class self_engine(Engine):
	pass


class Player5(Player):
	# Speed up players: only run through certain amount of memory bank
	MIN_CANDIDATES_COUNT = 10		# configure for small banks
	CANDIDATE_FRACTION = 0.2	# configure percentage for large banks

	def __init__(
		self, snapshot: PlayerSnapshot, ctx: GameContext = None, conversation_length: int = None
	) -> None:
		if ctx is not None:
			super().__init__(snapshot, ctx)
			self.ctx = ctx
			self.conversation_length = ctx.conversation_length
		else:
			super().__init__(snapshot, conversation_length)
			self.ctx = None
			self.conversation_length = conversation_length

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

	def propose_item(self, history: list[Item]) -> Item | None:
		if not self.memory_bank:
			return None
		
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

		# speed up player: run through either the min baseline(smaller memories) or a percentage(larger ones)
		candidates = max(self.MIN_CANDIDATES_COUNT, int(len(self.memory_bank) * self.CANDIDATE_FRACTION))
		top_candidates = self.memory_bank[:candidates]
		if not top_candidates:
			return None

		for item in top_candidates:
			new_history = history + [item]
			self.score_engine.history = new_history
			score = self.score_engine._Engine__calculate_scores()

			shared_ranking.append((item, score['shared']))
			pref_ranking.append((item, self.individual_score(item)))
			importance_ranking.append((item, item.importance))

		# Sort each list descending (best first)
		shared_ranking.sort(key=lambda x: x[1], reverse=True)
		pref_ranking.sort(key=lambda x: x[1], reverse=True)
		importance_ranking.sort(key=lambda x: x[1], reverse=True)

		# Build rank maps for quick lookup
		def build_rank_map(ranking):
			return {item: rank for rank, (item, _) in enumerate(ranking, start=1)}

		shared_map = build_rank_map(shared_ranking)
		pref_map = build_rank_map(pref_ranking)
		imp_map = build_rank_map(importance_ranking)

		# RRF parameters
		k = 60
		scores = {}
		# Nearing the end, maximize individaul score by preferring high importance topics
		turns_left = self.conversation_length - len(history)

		# Track subject repetition
		recent_subjects = [s for item in history[-3:] for s in item.subjects]
		count_recent = Counter(recent_subjects)

		# Add freshness bonus after pause
		last_pause = max((index for index, item in enumerate(history) if item is None), default=-1)
		history_post_pause = history[last_pause + 1:]
		subjects_post_pause = {subject for item in history_post_pause if item is not None for subject in item.subjects}

		for item in self.memory_bank:
			if turns_left <= 3:
				# lean into more important topics
				scores[item] = (
					1 / (k + shared_map.get(item, len(self.memory_bank)))
					+ 2 * (1 / (k + pref_map.get(item, len(self.memory_bank))))  
					+ 3 * (1 / (k + imp_map.get(item, len(self.memory_bank)))) # triple 
				)
			else:
				scores[item] = (
					1 / (k + shared_map.get(item, len(self.memory_bank)))
					+ 2 * (1 / (k + pref_map.get(item, len(self.memory_bank))))  # weight preferences higher
					+ 1 / (k + imp_map.get(item, len(self.memory_bank)))
				)

			if any(count_recent[subject] >= 3 for subject in item.subjects):
				# non-monotnous penalty
				scores[item] -= 1

			# freshness: count how many subjects of an item hasn't been mentioned since pause
			new_subject_count = sum(1 for subject in item.subjects if subject not in subjects_post_pause)
			scores[item] += new_subject_count

		# Pick best
		#best_item = max(scores.items(), key=lambda x: x[1])[0]
		best_score = max(scores.values())
		highest_candidates = [item for item, s in scores.items() if s == best_score]
		# if tied choose randomly so we don't constantly repeat picking the first max
		best_item = random.choice(highest_candidates)

		# remove after selection
		if best_item in self.memory_bank:
			self.memory_bank.remove(best_item)

		return best_item
