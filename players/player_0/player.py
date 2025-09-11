from models.player import Item, Player, PlayerSnapshot
from collections import Counter


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
	1. Calculate the score received in the past hist_depth turns
	2. Calculate the ratio between (Memory bank left) and (Length of remaining conversation)/Players 
	3. Determine the threshold using the two things we calculated in part 1 & 2
	'''
	def calculate_threshold(self, history: list[Item]) -> float:
		# num_players = 2 #change this line to whenever the instructor code is updated

		# '''
		# manipulatable variables

		# hist_depth represents how much of the history we want to take in account of for threshold calcs
		# turn_one_threshold dictates what actions we will do on turn 1. At -1000, it should always try to speak on turn 1
		# '''
		# hist_depth = 5 * num_players
		# turn_one_threshold = -1000

		# recent_turn_history = history[-hist_depth:]

		# if not recent_turn_history:
		# 	return turn_one_threshold  # default threshold on turn 1
		
		# hist_total_score = 0
		# count = 1
		# hist_all_but_last = history[:-1]
		# for item in hist_all_but_last:
		# 	if item is not None:
		# 		_, score, _ = self.calculate_score(item, history)
		# 		hist_total_score += score
		# 		count += 1
		# 		#print("His: " + str(score))
		# hist_avg_score = hist_total_score / count
		# return 0
		# #return hist_avg_score

		num_players = 2
		hist_depth = 5 * num_players
		turn_one_threshold = -1000

		if history == []:
			return turn_one_threshold

		recent_history = history[:-hist_depth]

		score_without_recent_history = self.calculate_history_score(recent_history)
		total_score = self.calculate_history_score(history)

		score_delta = total_score - score_without_recent_history
		avg_score_per_turn = score_delta / (len(history) - len(recent_history))
		

		#part 2 not implemented yet since we don't have access to # of players and stuff
		#part 3 not implemented yet

		threshold = avg_score_per_turn
		return threshold
	
	def calculate_item_score(self, item, history: list[Item]) -> tuple[Item, float]:
		history_score = self.calculate_history_score(history)
		history_score_with_item = self.calculate_history_score(history + [item])
		delta = history_score_with_item - history_score

		return item, delta

	
	def calculate_history_score(self, history: list[Item]) -> float:

		def calculate_freshness_score(i: int, current_item: Item) -> float:
			if i == 0 or history[i - 1] is not None:
				return 0.0

			prior_items = (item for item in history[max(0, i - 6) : i - 1] if item is not None)
			prior_subjects = {s for item in prior_items for s in item.subjects}

			novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]

			return float(len(novel_subjects))

		def calculate_coherence_score(i: int, current_item: Item) -> float:
			context_items = []

			for j in range(i - 1, max(-1, i - 4), -1):
				if history[j] is None:
					break
				context_items.append(history[j])
			
			for j in range(i + 1, min(len(history), i + 4)):
				if history[j] is None:
					break
				context_items.append(history[j])

			context_subject_counts = Counter(s for item in context_items for s in item.subjects)
			score = 0.0

			if not all(subject in context_subject_counts for subject in current_item.subjects):
				score -= 1.0

			if all(context_subject_counts.get(s, 0) >= 2 for s in current_item.subjects):
				score += 1.0

			return score

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

		unique_items = set()

		total_score = 0.0
		coherence_score = 0.0
		freshness_score = 0.0
		importance_score = 0.0
		nonmonotonousness = 0.0
		individual_score = 0.0

		for i, current_item in enumerate(history):
			if not current_item:
				continue

			if current_item.id in unique_items:
				nonmonotonousness += calculate_nonmonotonousness_score(i, current_item, repeated=True)
			else:
				importance_score += current_item.importance
				coherence_score += calculate_coherence_score(i, current_item)
				freshness_score += calculate_freshness_score(i, current_item)
				nonmonotonousness += calculate_nonmonotonousness_score(i, current_item, repeated=False)

				unique_items.add(current_item.id)
			
			bonuses = [1 - (self.preferences.index(s) / len(self.preferences)) for s in current_item.subjects]

			if current_item in self.memory_bank: # remove once TA updated code so that all items contributed impact individual score
				individual_score += sum(bonuses) / len(bonuses) 

		
		total_score = coherence_score + freshness_score + importance_score + nonmonotonousness + individual_score
	
		return total_score



	'''Calculate the fitness score using the greedy algorithm! Should be changed for optimization
	
	1. Takes an entire list of items
	2. For each item, calculate it's fitness score IF it is picked next
	3. Return the fitness score of the BEST item
	
	'''
	def calculate_greedy(self, history: list[Item]) -> tuple[Item, float] | None:
		if not self.memory_bank:
			return None

		item_scores = [self.calculate_item_score(item, history) for item in self.memory_bank]
		item_scores.sort(key=lambda x: x[1], reverse=True)
		return item_scores[0] #returns BEST item with its score