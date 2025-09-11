from abc import ABC, abstractmethod

from models.item import Item


class BaseStrategy(ABC):
	@abstractmethod
	def propose_item(self, history: list[Item]) -> Item | None:
		pass
