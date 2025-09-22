from collections import Counter

from models.player import GameContext, Item, Player, PlayerSnapshot

# player 6, 10

threshold_weight = 0
freshness_weight = 0
coherence_weight = 0
nonmonotonousness_weight = 0
individual_weight = 0
importance_weight = 0


class Player9(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		super().__init__(snapshot, ctx)

		self.starting_threshold = 1.8
		self.t1 = 1.05
		self.t2 = 1.1
		self.t3 = 1.2
		self.t4 = 1.5
		self.t5 = 3

	"""the important function where all the abstraction occurs!

	1. Calculates the delta bewteen the current total score and the total score contributed an item is for each item we have in our memory bank
	2. Calculate the threshold based on (a portion of our history) <-- the portion part is implemented in function
	3. Decide to pause or return the best item (we return the best item if it's score is greater than the threshold)
	
	"""

	def propose_item(self, history: list[Item]) -> Item | None:
		# conv length long = small decrease
		# many players = small decrease
		# memorybank left lots = small decrease
		if self.check_one_pause(history):
			ratio = (self.remaining_memory(history) * self.number_of_players) / (
				self.conversation_length - len(history)
			)
			if ratio > 1:
				self.starting_threshold = self.starting_threshold - (
					self.starting_threshold / (self.conversation_length - len(history))
				)
				self.starting_threshold = max(self.starting_threshold, 1)

		item_scores = self.calculate_greedy(history)  # [item, score]

		threshold = self.calculate_threshold(history)
		# threshold_weight = self.threshold_weight_adjustment() #uncomment this to add threshold weighting
		threshold = threshold * (1 + threshold_weight)
		# print ("threshold: " + str(threshold) + "   score: " + str(item_scores[1]))

		if not item_scores:  # just an edge case in case our memory is empty
			return None

		# print(item_scores[1], threshold)

		if item_scores[1] > threshold:
			return item_scores[0]
		if (
			self.check_two_pause(history) and item_scores[1] > 0.1
		):  # number is arbitrary, but should be at least 0
			return item_scores[0]
		if self.conversation_length == (len(history) + 1):  # last turn
			last_turn_threshold = max(0, max(self.conversation_length / 100, -1))
			if item_scores[1] > last_turn_threshold:
				return item_scores[0]
		return None

	"""Adjusts the threshold based on the number of turns and players in the game

	1. The longer the conversation, the higher the threshold (uses 10 turns as default)
	"""

	def threshold_weight_adjustment(self) -> int:
		default_iterations = 10
		total_iterations = self.conversation_length
		iteration_weight = (total_iterations - default_iterations) / default_iterations

		return iteration_weight * 0.1

	def check_one_pause(self, history: list[Item]) -> bool:
		# print (history)
		return len(history) >= 1 and history[-1] is None

	def check_two_pause(self, history: list[Item]) -> bool:
		# print (history)
		return len(history) >= 2 and history[-1] is None and history[-2] is None

	"""calculates the threshold needed for the player to speak

	1. Calculate the averagescore received in the past hist_depth turns
	2. Calculate the ratio between (Memory bank left) and (Length of remaining conversation)/Players 
	3. Determine the threshold using the two things we calculated in part 1 & 2
	"""

	def calculate_threshold(self, history: list[Item]) -> float:
		if self.check_one_pause(history):
			return 2

		if history == []:
			return -1000

		# mem * playernum : conversation length remaining
		ratio = (self.remaining_memory(history) * self.number_of_players) / (
			self.conversation_length - len(history)
		)
		if ratio > 2:
			return self.starting_threshold
		elif ratio > 1.5:
			return self.starting_threshold / self.t1
		elif ratio > 1:
			return self.starting_threshold / self.t2
		elif ratio > 0.75:
			return self.starting_threshold / self.t3
		elif ratio > 0.5:
			return self.starting_threshold / self.t4
		else:
			return self.starting_threshold / self.t5

	def remaining_memory(self, history: list[Item]) -> int:
		"""
		Returns how many items the player still has available to say
		(total memory length - number of times this player has already spoken).
		"""

		# count how many items from history belong to this player
		memory_bank_set = set(self.memory_bank)
		used = sum(1 for item in history if item in memory_bank_set)
		return len(self.memory_bank) - used

	"""Calculates the score contribution of a specific turn at a given index in the history

	1. Takes a history and an index
	2. Calculates the score contribution of the item at that specific index
	3. Returns the score contribution
	"""

	def calculate_turn_score(self, history: list[Item], index: int) -> float:
		if index >= len(history) or not history[index]:
			return 0.0

		current_item = history[index]

		# Returns the freshness score of an item
		def calculate_freshness_score(i: int, current_item: Item) -> float:
			if i == 0 or history[i - 1] is not None:
				return 0.0

			prior_items = (item for item in history[max(0, i - 6) : i - 1] if item is not None)
			prior_subjects = {s for item in prior_items for s in item.subjects}

			novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]

			return float(len(novel_subjects))

		# Returns the coherence score of an item
		def calculate_coherence_score(i: int, current_item: Item) -> float:
			context_items = []

			for j in range(i - 1, max(-1, i - 4), -1):
				if history[j] is None:
					break
				context_items.append(history[j])

			for j in range(i + 1, min(len(history), i + 4)):
				if history[j] is None or history[j] == current_item:
					break
				context_items.append(history[j])

			context_subject_counts = Counter(s for item in context_items for s in item.subjects)
			score = 0.0

			if not all(subject in context_subject_counts for subject in current_item.subjects):
				score -= 1.0

			if all(context_subject_counts.get(s, 0) >= 2 for s in current_item.subjects):
				score += 1.0

			return score

		# Returns the nonmonotonousness score of an item
		def calculate_nonmonotonousness_score(i: int, current_item: Item, repeated: bool) -> float:
			if repeated:
				return -1.0

			if i < 3:
				return 0.0

			last_three_items = [history[j] for j in range(i - 3, i)]
			if all(
				item and any(s in item.subjects for s in current_item.subjects)
				for item in last_three_items
			):
				return -1.0

			return 0.0

		# Check if this item is repeated in the history
		repeated = any(history[i] and history[i].id == current_item.id for i in range(index))

		# Calculate individual components
		coherence_score = 0.0
		freshness_score = 0.0
		importance_score = 0.0
		nonmonotonousness = 0.0
		individual_score = 0.0

		if not repeated:
			importance_score = current_item.importance
			coherence_score = calculate_coherence_score(index, current_item)
			freshness_score = calculate_freshness_score(index, current_item)

		nonmonotonousness = calculate_nonmonotonousness_score(index, current_item, repeated)

		# Calculate individual score
		bonuses = [
			1 - (self.preferences.index(s) / len(self.preferences)) for s in current_item.subjects
		]

		if bonuses:
			individual_score = sum(bonuses) / len(bonuses)

		# Return total score contribution
		return (
			coherence_score
			+ freshness_score
			+ importance_score
			+ nonmonotonousness
			+ individual_score
		)

	"""Calculates the score impact contributed by an item to the total score

	1. Calculates the direct score contribution of the new item
	2. Calculates how the new item affects the coherence scores of existing items
	3. Returning the total delta
	"""

	def calculate_item_score(self, item, history: list[Item]) -> tuple[Item, float]:
		# Calculate the direct score contribution of adding this item
		new_history = history + [item]
		direct_score = self.calculate_turn_score(new_history, len(new_history) - 1)

		# Calculate how this new item affects the coherence of existing items
		# Only items in the last 4 positions can be affected (due to coherence window)
		coherence_impact = 0.0
		items_to_check = min(4, len(history))

		for i in range(len(history) - items_to_check, len(history)):
			if history[i] is None:
				continue

			# Calculate old coherence score (without the new item)
			old_coherence = self.calculate_coherence_for_item_at_index(history, i)

			# Calculate new coherence score (with the new item)
			new_coherence = self.calculate_coherence_for_item_at_index(new_history, i)

			coherence_impact += new_coherence - old_coherence

		total_delta = direct_score + coherence_impact
		return item, total_delta

	def calculate_coherence_for_item_at_index(self, history: list[Item], index: int) -> float:
		"""Helper method to calculate coherence score for a specific item at a specific index."""
		if index >= len(history) or not history[index]:
			return 0.0

		current_item = history[index]
		context_items = []

		# Look at previous items (up to 4 back)
		for j in range(index - 1, max(-1, index - 4), -1):
			if history[j] is None:
				break
			context_items.append(history[j])

		# Look at future items (up to 4 forward)
		for j in range(index + 1, min(len(history), index + 4)):
			if history[j] is None or history[j] == current_item:
				break
			context_items.append(history[j])

		context_subject_counts = Counter(s for item in context_items for s in item.subjects)
		score = 0.0

		if not all(subject in context_subject_counts for subject in current_item.subjects):
			score -= 1.0

		if all(context_subject_counts.get(s, 0) >= 2 for s in current_item.subjects):
			score += 1.0

		return score

	"""Calculate the fitness score using the greedy algorithm! Should be changed for optimization
	
	1. Takes an entire list of items
	2. For each item, calculate it's fitness score IF it is picked next
	3. Return the fitness score of the BEST item
	
	"""

	def calculate_greedy(self, history: list[Item]) -> tuple[Item, float] | None:
		if not self.memory_bank:
			return None

		return max(
			(self.calculate_item_score(item, history) for item in self.memory_bank),
			key=lambda x: x[1],
			default=None,
		)
