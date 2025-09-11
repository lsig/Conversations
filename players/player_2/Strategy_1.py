import BaseStrategy

from models.item import Item


class Strategy1(BaseStrategy):
	def propose_item(self, history: list[Item]) -> Item | None:
		pass
