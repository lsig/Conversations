from models.player import Item, Player, PlayerSnapshot

# Creating a player for Group 10


class Player10(Player):
	"""
	Player for Group 10
	"""

	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		"""
		Initialize the player
		"""
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		"""
		Propose an item
		"""
		return None
