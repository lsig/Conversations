import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from models.item import Item


@dataclass(frozen=True)
class PlayerSnapshot:
	id: uuid.UUID
	preferences: tuple[int, ...]
	memory_bank: tuple[Item, ...]

	def item_in_memory_bank(self, item: Item):
		return item in self.memory_bank


@dataclass(frozen=True)
class GameContext:
	number_of_players: int
	conversation_length: int


class Player(ABC):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		self.id = snapshot.id
		self.name = type(self).__name__
		self.preferences = list(snapshot.preferences)
		self.memory_bank = list(snapshot.memory_bank)
		self.conversation_length = ctx.conversation_length
		self.number_of_players = ctx.number_of_players
		self.contributed_items = []

	def __str__(self) -> str:
		return f'ID: {self.id}\nName: {self.name}\nPreferences: {self.preferences}\nMemory Bank: {self.memory_bank}'

	def __repr__(self) -> str:
		return f'ID: {self.id}\nName: {self.name}\nPreferences: {self.preferences}\nMemory Bank: {self.memory_bank}'

	@abstractmethod
	def propose_item(self, history: list[Item]) -> Item | None:
		pass
