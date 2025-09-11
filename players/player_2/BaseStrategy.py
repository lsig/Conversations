from abc import ABC, abstractmethod

from models.item import Item
from models.player import Player


class BaseStrategy(ABC):
	@abstractmethod
	def propose_item(self, player: Player, history: list[Item]) -> Item | None:
		pass
