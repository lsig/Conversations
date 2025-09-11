from collections import Counter

from core.engine import Engine  # noqa: F821
from models.player import Item, Player, PlayerSnapshot


class self_engine(Engine):
	pass


class Player5(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

		self.snapshot = snapshot

		self.memory_bank.sort(key=lambda x: x.importance, reverse=True)
		self.best = self.memory_bank[0] if self.memory_bank else None

		self.turn_length = 0
		self.last_turn_position = -1

		self.recent_history = Counter()
		self.score_engine = None
		self.preferences = snapshot.preferences

	def individual_score(self, item: Item) -> float:
		# Individual score based on preference using the code in the game engine

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
		self.score_engine = self_engine(
			players=[],
			player_count=0,
			subjects=0,
			memory_size=len(self.memory_bank),
			conversation_length=self.conversation_length,
			seed=0,
		)

		self.score_engine.snapshots = [self.snapshot]

		res = []

		for item in self.memory_bank:
			new_history = history + [item]
			self.score_engine.history = new_history
			score = self.score_engine._Engine__calculate_scores()
			res = res + [(item, score['shared'] + self.individual_score(item), score)]

		res.sort(key=lambda x: x[1], reverse=True)

		# print("shared", res[0][2])

		return res[0][0] if res else None
