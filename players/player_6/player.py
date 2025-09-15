from models.player import Item, Player, PlayerSnapshot


class Player6(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)
		self.index = 0

	def propose_item(self, history: list[Item]) -> Item | None:
		# Sort the list in terms of subject rankings and importance
		self.memory_bank.sort(
			key=lambda item: (
				(
					self.preferences.index(item.subjects[0])
					+ self.preferences.index(item.subjects[1])
				)
				// 2
				if len(item.subjects) == 2
				else self.preferences.index(item.subjects[0]),
				-(item.importance),
			)
		)
		# create a reference list of all the items i can use so no repetitions happen
		unused_items = [item for item in self.memory_bank if item not in history]

		# Check if there should be a pause -> Have there been 3 consecutive items of the same subject
		best_item = unused_items[0]
		last_three = [item for item in history[-3:] if item is not None]
		if len(last_three) == 3:
			common_subjects = set(last_three[0].subjects)
			for item in last_three[1:]:
				common_subjects &= set(item.subjects)
			if common_subjects:
				return None

		# If there has not been 3 consecutive Items of the same subject, return the highest ranked item of the last subject, or if I have no items of that subject, just return my highest ranked item
		if history and history[-1] is not None:
			if any(sub in unused_items[-1].subjects for sub in best_item.subjects):
				if best_item not in history:
					return best_item
			else:
				for items in unused_items:
					if any(sub in history[-1].subjects for sub in items.subjects):
						return items
		else:
			return best_item
