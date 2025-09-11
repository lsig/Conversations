from models.player import Item, Player, PlayerSnapshot


class Player2(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		# Sort items by importance
		self.memory_bank.sort(key=lambda i: i.importance)
		# Check if all items used up
		if len(self.memory_bank) == 0:
			return None
		# Pick most important item and propose it
		last_item = self.memory_bank[-1]
		if len(history) != 0 and history[-1] == last_item:
			self.memory_bank.pop()
		return last_item
