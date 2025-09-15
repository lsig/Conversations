import random

from models.player import Item, Player, PlayerSnapshot


class RandomPlayer(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		return random.choice(self.memory_bank)
