from models.player import Item, Player, PlayerSnapshot


class Player3(Player):
<<<<<<< HEAD
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)
=======
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
		# optimal_p = Player3.best_p_value(self)
		print('optimal_p', optimal_p)
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
>>>>>>> parent of f20ced5 (Actually fixed the print issue)

	def propose_item(self, history: list[Item]) -> Item | None:
		return None
