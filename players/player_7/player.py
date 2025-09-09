from models.player import Item, Player, PlayerSnapshot


class Player7(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		max_importance = 0
		current = None

		subject_count = {subject: 0 for subject in self.preferences}
		
		for item in history:
			for subject in item.subjects:
				if subject in subject_count:
					subject_count[subject] += 1

		for item in self.memory_bank:
			for subject in item.subjects:
				if subject in subject_count and subject_count[subject] < 2:
					if item.importance > max_importance and item not in self.contributed_items:
						max_importance = item.importance
						current = item

		self.contributed_items.append(current)
		return current
	

		return None
