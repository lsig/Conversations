import heapq

from models.player import Item, Player, PlayerSnapshot


class Player3(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)
		self.ID_dict = dict()
		self.starters = []
		self.blocks = dict()
		High_topics = self.preferences[: len(self.preferences) // 2]
		for item in self.memory_bank:
			self.ID_dict[item.id] = item
			if len(item.subjects) == 2:
				continue
			if item.importance > 0.5:
				if item.subjects[0] in self.blocks:
					heapq.heappush(self.blocks[item.subjects[0]], (-item.importance, item.id))
				else:
					self.blocks[item.subjects[0]] = []
					heapq.heappush(self.blocks[item.subjects[0]], (-item.importance, item.id))
				if item.subjects[0] in High_topics:
					heapq.heappush(self.starters, (-item.importance, item.id))

	def propose_item(self, history: list[Item]) -> Item | None:
		seenID = set()
		for item in history:
			if item is not None:
				seenID.add(item.id)
		if len(history) < 2 or history[-1] is None or history[-2] is None:
			while True:
				if len(self.starters) > 0:
					(score, item_id) = heapq.heappop(self.starters)
					if item_id in seenID:
						continue
					heapq.heappush(self.starters, (score, item_id))
					return self.ID_dict[item_id]
				else:
					return None
		else:
			goalsuit = history[-2].subjects[0]
			if goalsuit not in self.blocks or len(self.blocks[goalsuit]) == 0:
				return None
			else:
				while True:
					if len(self.blocks[goalsuit]) > 0:
						(score, item_id) = heapq.heappop(self.blocks[goalsuit])
						if item_id in seenID:
							continue
						heapq.heappush(self.blocks[goalsuit], (score, item_id))
						return self.ID_dict[item_id]
					else:
						return None
