
from models.player import Item, Player, PlayerSnapshot, GameContext


class Player7(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)

	def propose_item(self, history: list[Item]) -> Item | None:
		current = None
		max_score = 0

		subject_count = {subject: 0 for subject in self.preferences}
		for item in history[-3:]:
			if item is None:
				continue
			for subject in item.subjects:
				subject_count[subject] += 1

		for item in self.memory_bank:
			if item in self.contributed_items:
				continue
			score = item.importance
			for subject in item.subjects:
				if subject_count[subject] > 0:
					score += 1
			if score > max_score:
				max_score = score
				current = item

		self.contributed_items.append(current)
		return self.pause(history)

	def pause(self, history: list[Item]) -> Item | None:
		
		rejected: list[Item] = list()
		subject = -1
		
		# look through preferences in most to least important order
		for p in self.preferences:
			# check history of last 5 items to see if preference has been mentioned recently and if it has skip
			if p not in history[:-5]:
				for item in self.memory_bank:
					#check if p is in the subejcts of an item, not in history, and greater importance than arbitrary theshold
					if p in item.subjects and item not in history and item.importance > 0.5:
						return item
					else:
						rejected.append(item)
		
		return rejected[0] if rejected else None