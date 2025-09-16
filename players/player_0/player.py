from models.player import Item, Player, PlayerSnapshot, GameContext


class Player0(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		super().__init__(snapshot, ctx)

	def propose_item(self, history: list[Item]) -> Item | None:
		return None
