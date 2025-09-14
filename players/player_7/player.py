
from models.player import Item, Player, PlayerSnapshot, GameContext


class Player7(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)

	def propose_item(self, history: list[Item]) -> Item | None:
		if len(history) > 0:
			if history[-1] is not None and history[-1].player_id == self.id:
				self.contributed_items.append(history[-1])

		# if its first turn or previous was a pause
		if len(history) == 0 or history[-1] is None:
			return self.pause(history)
		else:
			return self.play(history)
		


	def pause(self, history: list[Item]) -> Item | None:
		
		rejected: list[Item] = list()
		
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
	
	def play(self, history: list[Item]) -> Item | None:
		subject_count = {subject: 0 for subject in self.preferences}
		# tracks how many times each subject has been mentioned in the last 3 said items
		for item in history[-3:]:
			if item is None:
				continue
			for subject in item.subjects:
				subject_count[subject] += 1

		preference_threshold = len(self.preferences) // 2
		chosen_item = None
		importance = float('-inf')
		highest_pref_index = float('inf')

		# look through memory bank, find item in top half of preference list that has been mentioned recently and has highest importance
		for item in self.memory_bank:
			if item in history:
				continue
			for subject in item.subjects:
				times_mentioned = subject_count[subject]
				pref_index = self.preferences.index(subject) # get index of subject in preferences list
				if times_mentioned in range(0, 3) and subject in self.preferences[0:preference_threshold]:  # noqa: SIM102
					if pref_index < preference_threshold or (pref_index ==highest_pref_index and item.importance > importance):
						chosen_item = item
						importance = item.importance
		return chosen_item if chosen_item else None
		# If no item has been chosen so far, then loop through memory bank and find the item that has highest importance and is not in history.
		if chosen_item is None:
			for item in self.memory_bank:
				if item not in history:
					if item.importance > importance:
						chosen_item = item
						importance = item.importance
		# Return item with highest importance that is not in history.
		return chosen_item

			

		
