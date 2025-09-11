from models.player import Item, Player, PlayerSnapshot


class Player0(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	'''the important function where all the abstraction occurs!

	1. Calculates what the 'item score' is for each item we currently have in memory bank
	2. Calculate the threshold based on (a portion of our history) <-- the portion part is implemented in function
	3. Decide to pause or return the best item
	
	'''
	def propose_item(self, history: list[Item]) -> Item | None:
		item_scores = self.calculate_greedy(history) #[item, score]
		threshold = self.calculate_threshold(history)
		if not item_scores: #just an edge case in case our memory is empty
			return None
	
		if item_scores[1] > threshold:
			return item_scores[0]
		else:
			return None
	
	'''calculates the threshold needed for the player to speak
	1. Calculate the score received in the past hist_depth turns (I hate that this is a step and not premade for us, you might need to redo this)
	2. Calculate the ratio between (Memory bank left) and (Length of remaining conversation)/Players 
	3. Determine the threshold using the two things we calculated in part 1 & 2
	'''
	def calculate_threshold(self, history: list[Item]) -> float:
		num_players = 2 #change this line to whenever the instructor code is updated

		'''
		manipulatable variables

		hist_depth represents how much of the history we want to take in account of for threshold calcs
		turn_one_threshold dictates what actions we will do on turn 1. At -1000, it should always try to speak on turn 1
		'''
		hist_depth = 5 * num_players
		turn_one_threshold = -1000

		recent_turn_history = history[-hist_depth:]

		if not recent_turn_history:
			return turn_one_threshold  # default threshold on turn 1
		
		hist_total_score = 0
		count = 1
		hist_all_but_last = history[:-1]
		for item in hist_all_but_last:
			if item is not None:
				_, score = self.calculate_score(item, history)
				hist_total_score += score
				count += 1
		hist_avg_score = hist_total_score / count

		#part 2 not implemented yet since we don't have access to # of players and stuff

		#part 3 not implemented yet
		threshold = 0
		return threshold
		#return hist_avg_score
	
	def calculate_score(self, item, history: list[Item]) -> tuple[Item, float]:
		coherence_bonus = 0
		importance_bonus = item.importance
		freshness_bonus = 0
		nonmonotonousness_bonus = 0
		individual_bonus = 0

		# calculate coherence bonus
		recent_items = []
		for history_item in reversed(history):
			if history_item is None:
				break
			if history_item is not None:
				recent_items.append(history_item)
				if len(recent_items) >= 3:
					break

		history_subjects = {}
		for i in recent_items:
			for s in i.subjects:
				history_subjects[s] = history_subjects.get(s, 0) + 1

		if len(item.subjects) == 1:
			if history_subjects.get(item.subjects[0], 0) == 0:
				coherence_bonus -= 0
			elif history_subjects.get(item.subjects[0], 0) == 1:
				coherence_bonus += 0.5
			elif history_subjects.get(item.subjects[0], 0) >= 2:
				coherence_bonus += 1
		else:
			if (
				history_subjects.get(item.subjects[0], 0) == 0
				and history_subjects.get(item.subjects[1], 0) == 0
			):
				coherence_bonus -= 0
			elif (
				history_subjects.get(item.subjects[0], 0) == 1
				and history_subjects.get(item.subjects[1], 0) == 1
			):
				coherence_bonus += 0.5
			elif (
				history_subjects.get(item.subjects[0], 0) >= 2
				and history_subjects.get(item.subjects[1], 0) >= 2
			):
				coherence_bonus += 1 

		# calculate freshness bonus
		if len(history) >= 1 and history[-1] is None:
			recent_items = []
			for history_item in reversed(history):
				recent_items.append(history_item)
				if len(recent_items) >= 5:
					break
			history_subjects = set()
			for i in recent_items:
				history_subjects.update(i.subjects)
			if len(item.subjects) == 1:
				if item.subjects[0] not in history_subjects:
					freshness_bonus += 1
			else:
				if (
					item.subjects[0] not in history_subjects
					and item.subjects[1] not in history_subjects
				):
					freshness_bonus += 1

		# calculate nonmonotonousness bonus
		if len(history) >= 3:
			recent_items = history[-3:]
			history_subjects = {}
			for i in recent_items:
				for s in i.subjects:
					history_subjects[s] = history_subjects.get(s, 0) + 1

			for s in history_subjects:
				if s in item.subjects and history_subjects[s] >= 3:
					nonmonotonousness_bonus -= 1

		# calculate repetition impact
		for i in history:
			if i.id == item.id:
				coherence_bonus = 0
				importance_bonus = 0
				freshness_bonus = 0
				nonmonotonousness_bonus -= 1
				break

		# calculate individual bonus

		for s in item.subjects:
			rank = self.preferences.index(s)
			bonus = 1 - (rank / len(self.preferences))
			individual_bonus += bonus / len(item.subjects)

		# calculate total bonus
		total_bonus = (
			coherence_bonus
			+ importance_bonus
			+ freshness_bonus
			+ nonmonotonousness_bonus
			+ individual_bonus
		)
		total_bonus = sum(
			(
				total_bonus,
				coherence_bonus,
				importance_bonus,
				freshness_bonus,
				nonmonotonousness_bonus,
				individual_bonus,
			)
		)
		return item, total_bonus


	'''Calculate the fitness score using the greedy algorithm! Should be changed for optimization
	
	1. Takes an entire list of items
	2. For each item, calculate it's fitness score IF it is picked next
	3. Return the fitness score of the BEST item
	
	'''
	def calculate_greedy(self, history: list[Item]) -> tuple[Item, float] | None:
		if not self.memory_bank:
			return None

		item_scores = [self.calculate_score(item, history) for item in self.memory_bank]
		item_scores.sort(key=lambda x: x[1], reverse=True)
		return item_scores[0] #returns BEST item with its score