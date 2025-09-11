from abc import ABC, abstractmethod

from models.item import Item
from models.player import PlayerSnapshot


class BaseStrategy(ABC):
	@abstractmethod
	def propose_item(self, snapshot: PlayerSnapshot, history: list[Item]) -> Item | None:
		pass
