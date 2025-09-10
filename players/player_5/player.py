import itertools
from collections import Counter

from models.player import Item, Player, PlayerSnapshot


class Player5(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)
		self.memory_bank.sort(key=lambda x: x.importance, reverse=True)
		self.best = self.memory_bank[0] if self.memory_bank else None


	def propose_item(self, history: list[Item]) -> Item | None:

		if(len(self.memory_bank) == 0):
			return None
		choice = self.memory_bank[0]

		# no history -> just talk about the most important thing we have
		if len(history) == 0:
			self.memory_bank.remove(choice)
			return choice
		
		# start with worst
		choice = self.memory_bank[-1]

		# look back up to 3 turns
		clen = min(3, len(history))
		recent = history[-clen:]

		# get subjects from most recent items
		subjects = []
		for r in recent:
			subjects.append(r.subjects)
		result = list(itertools.chain(*subjects))
		count = Counter(result)

		#print("History", history[-1].subjects)

		# look for better candidate
		for item in self.memory_bank:
			# reset inside each time
			fail = False

			for subject in item.subjects:
				#print("subject", subject, "in", history[-1].subjects, "count", count[subject])
				if count[subject] > 2 or subject in history[-1].subjects:
					fail = True
					break


			if not fail:
				fail = False
				# prefer higher importance if available
				if item.importance > choice.importance:
					choice = item 

		# remove chosen item from memory bank
		if choice in self.memory_bank:
			self.memory_bank.remove(choice)

		return choice


