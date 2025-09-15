from models.player import GameContext, Item, Player, PlayerSnapshot
from players.player_2.BaseStrategy import BaseStrategy
from players.player_2.Strategy_1 import Strategy1
from players.player_2.Strategy_2 import Strategy2


class Player2(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)
		self.snapshot = snapshot
		self.subject_num: int = len(self.preferences)
		self.memory_bank_size: int = len(self.memory_bank)
		self.current_strategy: BaseStrategy = None
		self.sub_to_item: dict = {}
		self.last_proposed_item: Item = None

		self._init_sub_to_item()

		self._choose_strategy()

	def propose_item(self, history: list[Item]) -> Item | None:
		return self.current_strategy.propose_item(self, history)

	def _choose_strategy(self):
		self.current_strategy = Strategy1()
		# if self.subject_num / self.memory_bank_size <= 0.5:
		# 	self.current_strategy = Strategy1()
		# else:
		# 	self.current_strategy = Strategy2()

	def _init_sub_to_item(self):
		for item in self.memory_bank:
			subjects = tuple(sorted(list(item.subjects)))
			if subjects not in self.sub_to_item:
				self.sub_to_item[subjects] = []
			self.sub_to_item[subjects].append(item)
