from models.player import Item, Player, PlayerSnapshot
from players.player_11.do_something import do_something


class Player11(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		do_something()
		for mb in self.memory_bank:
			print(f'importance: {mb.importance}')
		return None
