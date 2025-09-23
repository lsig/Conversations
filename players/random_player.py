import random

from models.player import GameContext, Item, Player, PlayerSnapshot


class RandomPlayer(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)

	def propose_item(self, history: list[Item]) -> Item | None:
		return random.choice(self.memory_bank)
