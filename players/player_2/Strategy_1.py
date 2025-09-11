import BaseStrategy

from models.item import Item
from models.player import PlayerSnapshot


class Strategy1(BaseStrategy):
	def propose_item(self, snapshot: PlayerSnapshot, history: list[Item]) -> Item | None:
		pass
