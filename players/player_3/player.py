import heapq

from models.player import GameContext, Item, Player, PlayerSnapshot


class Player3(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)
		self.ID_dict = dict()
		# maps IDs to items

		self.blocks = dict()
		# Good conversation continuers "middle of the zipper"

		self.High_topics = self.preferences[: len(self.preferences) // 2]

		self.started_subject = set()

		self.previous_item = [-1]

		# Sets self.starters to be a heap of items that have high importance and high self value
		# sets self.blocks to be a heap of items that have high importance
		optimal_p = Player3.best_p_value(self)
		# print('optimal_p', optimal_p)
		for item in self.memory_bank:
			self.ID_dict[item.id] = item
			if len(item.subjects) == 2:
				continue

			if item.importance > optimal_p:
				if item.subjects[0] in self.blocks:
					heapq.heappush(self.blocks[item.subjects[0]], (-item.importance, item.id))
				else:
					self.blocks[item.subjects[0]] = []
					heapq.heappush(self.blocks[item.subjects[0]], (-item.importance, item.id))

	# Determine the best value to lower bound our potential block conversation
	# We want there to be at least 4 of any single block, but then we try to spread it out
	def best_p_value(self):
		memory = len(self.memory_bank)
		length = self.conversation_length
		players = self.number_of_players
		temp_subject_count = max(max(self.memory_bank, key=lambda x: x.subjects).subjects)

		TotalBlocks = memory * players / 2

		blocks_per_subject = TotalBlocks / temp_subject_count

		at_least_4 = 4 / blocks_per_subject

		optimal = (length * 1.2) / temp_subject_count / blocks_per_subject

		return min(1 - at_least_4, 1 - optimal)

	def readd(self, item):
		if item.importance > 0.5:
			if item.subjects[0] in self.blocks:
				heapq.heappush(self.blocks[item.subjects[0]], (-item.importance, item.id))
			else:
				self.blocks[item.subjects[0]] = []
				heapq.heappush(self.blocks[item.subjects[0]], (-item.importance, item.id))

	def propose_item(self, history: list[Item]) -> Item | None:
		# Maintain a set of topics already started
		if len(history) == 1 and history[-1] is not None:
			self.started_subject.add(history[-1].subjects[0])
		if len(history) == 2 and history[-1] is not None:
			self.started_subject.add(history[-1].subjects[0])
		elif len(history) > 2:
			if history[-2] is None and history[-1] is not None:
				self.started_subject.add(history[-1].subjects[0])
			if history[-3] is None and history[-1] is not None:
				self.started_subject.add(history[-1].subjects[0])

		if (
			len(history) > 0
			and self.previous_item[0] != -1
			and history[-1] != self.ID_dict[self.previous_item[0]]
		):
			Player3.readd(self, self.ID_dict[self.previous_item[0]])

		# Start a conversation with our best conversation opener
		if len(history) < 2 or history[-1] is None:
			best_subject = None
			best_importance = 0
			for subject in self.blocks:
				if subject in self.started_subject:
					continue
				if len(self.blocks[subject]) > 0:
					(cur_importance, id) = self.blocks[subject][0]
					if -cur_importance > best_importance:
						best_subject = subject
						best_importance = -cur_importance
			if best_subject is None:
				self.previous_item = [-1]
				return None
			else:
				(score, item_id) = heapq.heappop(self.blocks[best_subject])
				self.previous_item[0] = item_id
				return self.ID_dict[item_id]

		# Start a second conversation with our best conversation opener
		# While making sure we don't repeat a topic
		elif history[-2] is None:
			avoid = history[-1].subjects[0]
			best_subject = None
			best_importance = 0
			for subject in self.blocks:
				if subject in self.started_subject:
					continue
				if subject == avoid:
					continue
				if len(self.blocks[subject]) > 0:
					(cur_importance, id) = self.blocks[subject][0]
					if -cur_importance > best_importance:
						best_subject = subject
						best_importance = -cur_importance
			if best_subject is None:
				self.previous_item = [-1]
				return None
			else:
				(score, item_id) = heapq.heappop(self.blocks[best_subject])
				self.previous_item[0] = item_id
				return self.ID_dict[item_id]

		# Continue the conversation
		else:
			goalsuit = history[-2].subjects[0]
			if goalsuit not in self.blocks or len(self.blocks[goalsuit]) == 0:
				self.previous_item = [-1]
				return None
			else:
				(score, item_id) = heapq.heappop(self.blocks[goalsuit])
				self.previous_item[0] = item_id
				return self.ID_dict[item_id]
