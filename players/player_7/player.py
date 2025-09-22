from models.player import GameContext, Item, Player, PlayerSnapshot
from collections import defaultdict

class Player7(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)
		# track subject relevance and mentions across all players
		self.game_subject_relevance = defaultdict(float)
		self.game_subject_mentions = defaultdict(int)

	def propose_item(self, history: list[Item]) -> Item | None:
		if len(history) == 0:
			return None
		
		if len(history) > 0 and history[-1] is not None and history[-1].player_id == self.id:
			self.contributed_items.append(history[-1])

		self.update_game_preferences(history)

		# if its first turn or previous was a pause
		if len(history) == 0 or history[-1] is None:
			return self.pause(history)
		else:
			return self.play(history)

	def pause(self, history: list[Item]) -> Item | None:
		# look through preferences in most to least important order
		for p in self.preferences:
			# when history is less than 5, just propose the first item that matches preference and has high importance
			if len(history) < 5:
				for item in self.memory_bank:
					if p in item.subjects and item.importance > 0.5:
						return item

			# check history of last 5 items to see if preference has been mentioned recently and if it has skip
			elif len(history) >= 5 and p not in [s for item in history[-5:] if item for s in item.subjects]:
				for item in self.memory_bank:
					# check if p is in the subjects of an item, not in history, and greater importance than arbitrary threshold
					if p in item.subjects and item not in history and item.importance > 0.5:
						return item

		return None

	def play(self, history: list[Item]) -> Item | None:
		subject_count = {subject: 0 for subject in self.preferences}
		
		# tracks how many times each subject has been mentioned in the last 3 said items
		for item in history[-3:]:
			if item is None:
				continue
			for subject in item.subjects:
				if subject in subject_count:
					subject_count[subject] += 1

		remaining = [it for it in self.memory_bank if it not in history]
		
		if not remaining:
			return None  
			
		K = self.dynamic_threshold(history)
		eligible = [it for it in remaining if self.most_preferred(it) <= K]
		
		# if dynamic threshold is too restrictive, return None rather than lowering standards
		if not eligible:
			return None
		
		chosen_item = None
		best_score = float('-inf')

		# look through memory bank, find item that balances personal preferences, game relevance, and coherence
		for item in eligible:
			pref_index = self.most_preferred(item)
			most_preferred_subject = self.preferences[pref_index]
			times_mentioned = subject_count.get(most_preferred_subject, 0)
			
			# only consider items that maintain coherence (mentioned 1-2 times recently)
			if times_mentioned not in range(1, 3):
				continue

			item_score = self.calculate_item_score(item, pref_index)

			if item_score > best_score:
				chosen_item = item
				best_score = item_score

		# return chosen item or None if no item meets our strategic criteria
		return chosen_item

	def calculate_item_score(self, item: Item, pref_index: int) -> float:
		# personal preference component (higher is better, so invert the index)
		personal_pref_score = 1.0 - (pref_index / (len(self.preferences) - 1))
		
		# item importance component
		importance_score = item.importance

		# game relevance component - how well does this item align with game preferences?
		game_relevance_score = self.get_game_relevance_score(item)

		# weighted combination - can be adjusted
		personal_weight = 0.5     # Personal preference
		importance_weight = 0.2   # Item importance
		game_weight = 0.3         # Game flow/relevance
		
		total_score = (
			personal_weight * personal_pref_score +
			importance_weight * importance_score +
			game_weight * game_relevance_score
		)
		
		return total_score

	def get_game_relevance_score(self, item: Item) -> float:
		if not self.game_subject_relevance:
			return 0.5  # neutral score if no game data yet

		item_relevance_scores = []

		for subject in item.subjects:
			# get the relevance score for this subject
			relevance = self.game_subject_relevance.get(subject, 0.0)
			mentions = self.game_subject_mentions.get(subject, 0)
			
			# normalize by how often it's been mentioned (avoid division by zero)
			# punish subjects that are over-mentioned for entire game
			norm_relevance = relevance / mentions if mentions > 0 else 0.0
			item_relevance_scores.append(norm_relevance)

		# return average relevance score for this item's subjects
		return sum(item_relevance_scores) / len(item_relevance_scores) if item_relevance_scores else 0.0

	def update_game_preferences(self, history: list[Item]) -> None:
		if len(history) == 0:
			return
		
		# update subject mention counts for the new item only
		if history[-1] is not None:
			for subject in history[-1].subjects:
				self.game_subject_mentions[subject] += 1

		# analyze continuation patterns for the current transition
		# ex: if history = [A, B, C] analyze transition from B -> C
		if len(history) >= 2:
			
			if history[-2] is not None and history[-1] is not None:
				previous_subjects = set(history[-2].subjects)
				current_subjects = set(history[-1].subjects)

				# Subjects that got continued or dropped in this transition
				continued_subjects = set()

				for subject in previous_subjects:
					if subject in current_subjects:
						continued_subjects.add(subject)

				dropped_subjects = set()

				for subject in previous_subjects:
					if subject not in current_subjects:
						dropped_subjects.add(subject)
				
				# can be adjusted, might need better metric
				recency_weight = 0.2 # weight recent transitions more
				
				for subject in continued_subjects:
					self.game_subject_relevance[subject] += recency_weight * 1.0

				for subject in dropped_subjects:
					self.game_subject_relevance[subject] += recency_weight * -0.3

		# analyze new cluster patterns in the last 3 items
		self.analyze_subject_clusters(history)

	# check last 3 items in history for subject clusters
	def analyze_subject_clusters(self, history: list[Item]) -> None:
		if len(history) < 3:
			return

		subject_counts = defaultdict(int)

		for item in history[-3:]:
			if item is not None:
				for subject in item.subjects:
					subject_counts[subject] += 1
		
		# subjects that appear 1 or 2 times in the window get a small relevance boost
		# subjects that appear 3 or more times get a staleness penalty
		for subject, count in subject_counts.items():
			if count in [1, 2]:  
				relevance_bonus = count * 0.2
				self.game_subject_relevance[subject] += relevance_bonus

			elif count >= 3:  
				staleness_penalty = count * 0.5
				self.game_subject_relevance[subject] -= staleness_penalty


	def most_preferred(self, item: Item) -> int:
		# return the index of the most preferred subject in the item
		return min([self.preferences.index(s) for s in item.subjects if s in self.preferences])


	def dynamic_threshold(self, history) -> int:
		# return a dynamic threshold based on the history length
		progress = min(1, len(self.contributed_items) / (max(1, len(self.memory_bank)))) # 0->1
		S = len(self.preferences)
		K = int(S * (0.30 + 0.40 * progress)) - 1  # 30% -> 70% as bank shrinks
		return max(0, min(S - 1, K))