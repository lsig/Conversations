from models.player import GameContext, Item, Player, PlayerSnapshot


class Player10(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)

	def propose_item(self, history: list[Item]) -> Item | None:
		return None
