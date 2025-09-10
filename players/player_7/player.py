from models.player import Item, Player, PlayerSnapshot


class Player7(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		current = None
		max_score = 0

		subject_count = {subject: 0 for subject in self.preferences}
		for item in history[-3:]:
			for subject in item.subjects:
				subject_count[subject] += 1

		for item in self.memory_bank:
			if item in self.contributed_items:
				continue 
			score = item.importance
			for subject in item.subjects:
					if subject_count[subject] > 0:
						score +=1
			if score > max_score:
				max_score = score
				current = item
			
		
		self.contributed_items.append(current)
		return current
	

