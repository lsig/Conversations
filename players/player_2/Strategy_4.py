from players.player_2.BaseStrategy import BaseStrategy


from models.item import Item
from models.player import Player


class Strategy4(BaseStrategy):
	def propose_item(self, player: Player, history: list[Item]) -> Item | None:
		pass
