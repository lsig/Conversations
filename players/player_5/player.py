from models.player import Item, Player, PlayerSnapshot
import random
import itertools

from collections import Counter

class Player5(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)
		self.memory_bank.sort(key=lambda x: x.importance, reverse=True)
		self.best = self.memory_bank[0]





	def propose_item(self, history: list[Item]) -> Item | None:

		if(len(self.memory_bank) == 0):
			return None
		choice = self.memory_bank[0]
	
		if len(history) == 0:
			self.memory_bank.remove(choice)
			return choice
		
		choice = self.memory_bank[-1]

		clen = 3 if len(history) > 3 else len(history)
		recent = history[-1 * clen:]

		subjects = []
		for r in recent:
			subjects.append(r.subjects)

		result = list(itertools.chain(*subjects))
		count = Counter(result)

		fail = False

		#print("History", history[-1].subjects)

		for item in self.memory_bank:
			for subject in item.subjects:
				#print("subject", subject, "in", history[-1].subjects, "count", count[subject])
				if count[subject] > 2 or subject in history[-1].subjects:
					fail = True
					break


			if not fail:
				fail = False
				choice = item if item.importance > choice.importance else choice 	

		self.memory_bank.remove(choice)

		return choice


