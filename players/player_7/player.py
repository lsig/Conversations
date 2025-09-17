from models.player import GameContext, Item, Player, PlayerSnapshot
import statistics

class Player7(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)

	def propose_item(self, history: list[Item]) -> Item | None:
		if len(history) > 0 and history[-1] is not None and history[-1].player_id == self.id:
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
			# when history is less than 5, just propose the first item that matches preference and has high importance
			if len(history) < 5:
				for item in self.memory_bank:
					if p in item.subjects and item.importance > 0.5:
						return item

			# check history of last 5 items to see if preference has been mentioned recently and if it has skip
			elif len(history) >= 5 and p not in history[:-5]:
				for item in self.memory_bank:
					# check if p is in the subejcts of an item, not in history, and greater importance than arbitrary theshold
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

		remaining = [it for it in self.memory_bank if it not in history]
		K = self.dynamic_threshold(history)
		eligible = [it for it in remaining if self.most_preferred(it) <= K]
		if not eligible:  # safety valve
			eligible = remaining
		chosen_item = None
		importance = float('-inf')
		highest_pref_index = float('inf')

		# look through memory bank, find item in top half of preference list that has been mentioned recently and has highest importance
		for item in eligible:
			subject = self.preferences[self.most_preferred(item)]
			times_mentioned = subject_count[subject]
			pref_index = self.preferences.index(
				subject
			)
			print(subject, times_mentioned, item.importance, pref_index)
			# get index of subject in preferences list
			# formatted long if using copilot
			if (
				times_mentioned in range(1, 3)
				and (
					pref_index < highest_pref_index  # if item is higher in preference list, choose it
					or (pref_index == highest_pref_index and item.importance > importance) #if two items have the same subject, say the more important one
				)
			):
				chosen_item = item
				importance = item.importance
				highest_pref_index = pref_index


		### new code below
		# calculate average importance of remaining items
		avg = statistics.mean([item.importance for item in remaining]) if remaining else 0

		#calculate median importance of remaining items
		med = statistics.median([item.importance for item in remaining]) if remaining else 0

		#if no item is coherent and preferred we say something preferred and important > 0.5 if you cant then pause
		if chosen_item is None:
			for item in self.memory_bank:
				if self.most_preferred(item) <= K and item.importance > .5:
					chosen_item = item
					return chosen_item
			return None  # pause if no item found
		
		return chosen_item if chosen_item else None

		### old code below
		# # If no item has been chosen so far, then loop through memory bank and find the item that has highest importance and is not in history.
		# if chosen_item is None:
		# 	for item in self.memory_bank:
		# 		if item not in history and item.importance > importance:
		# 			chosen_item = item
		# 			importance = item.importance
		# # Return item with highest importance that is not in history.
		
	
	def most_preferred(self,item:Item)->int:
		# return the most preferred subject in the item
		return min([self.preferences.index(s) for s in item.subjects])
	
	def dynamic_threshold(self,history:list[Item])->int:
		# return a dynamic threshold based on the history length
		remaining = [item for item in self.memory_bank if item not in history]
		said = len(self.contributed_items)
		progress = min(1, said/ (max(1,len(self.memory_bank)) ))  # 0→1
		S = len(self.preferences)
		K = int(S * (0.50 + 0.40 * progress)) - 1  # 50% -> 90% as bank shrinks
		return max(0, min(S - 1, K))





