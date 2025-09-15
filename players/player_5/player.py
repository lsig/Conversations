from collections import Counter

from core.engine import Engine  # noqa: F821
from models.player import GameContext, Item, Player, PlayerSnapshot


class self_engine(Engine):
	pass


class Player5(Player):
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

		# NOTE: if player speed is slow likely because of this
		for item in self.memory_bank:
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

		for item in self.memory_bank:
			scores[item] = (
				1 / (k + shared_map[item])
				+ 2 * (1 / (k + pref_map[item]))  # weight preferences higher
				+ 1 / (k + imp_map[item])
			)

		# Pick best
		best_item = max(scores.items(), key=lambda x: x[1])[0]
		# remove after selection
		if best_item in self.memory_bank:
			self.memory_bank.remove(best_item)
			
		return best_item
