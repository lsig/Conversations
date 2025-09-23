from collections import Counter, defaultdict

from models.player import GameContext, Item, Player, PlayerSnapshot

# import uuid
# import random


class Player6(Player):
	def _init_(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super()._init_(snapshot, ctx)

	# def __game_context(ctx, history, i: int):
	# 	L = ctx.conversation_length
	# 	P = ctx.number_of_players
	# 	n = len(history)
	# 	#for items in history:
	# 	prior_items = (item for item in history[max(0, n - 6) : n - 1] if item is not None)
	# 	prior_subjects = {s for item in prior_items for s in item.subjects}

	# 	last_three_items = [history[j] for j in range(n - i, n)]

	def __calculate_freshness_score(self, history, i: int, current_item: Item) -> float:
		if i == 0 or history[i - 1] is not None:
			return 0.0

		prior_items = (item for item in history[max(0, i - 6) : i - 1] if item is not None)
		prior_subjects = {s for item in prior_items for s in item.subjects}

		novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]

		return float(len(novel_subjects))

	def __calculate_coherence_score(self, history, i: int, current_item: Item) -> float:
		context_items = []

		for j in range(i - 1, max(-1, i - 4), -1):
			if history[j] is None:
				break
			context_items.append(history[j])

		for j in range(i + 1, min(len([history]), i + 4)):
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

	def __calculate_nonmonotonousness_score(
		self, history, i: int, current_item: Item, repeated: bool
	) -> float:
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

	def __calculate_individual_score(self, current_item: Item) -> float:
		return current_item.importance

	def propose_item(self, history: list[Item]) -> Item | None:
		weight_nonMon = 2.0
		best_item: Item = None
		best_score = -0.1
		n = len(history)

		# check if it is the first item in the conversation
		subject_dict = defaultdict(int)
		first_importance = float('-inf')
		if n == 0:
			for items in self.memory_bank:
				for subject in items.subjects:
					subject_dict[subject] += 1

			max_freq = max(subject_dict.values())
			tied_subjects = [sub for sub, count in subject_dict.items() if count == max_freq]
			best_subject = min(tied_subjects, key=lambda s: self.preferences.index(s))

			for item in self.memory_bank:
				if best_subject in item.subjects and item.importance > first_importance:
					first_importance = item.importance
					best_item = item

		else:
			id_list = []
			contributed_items = []
			if history is not None:
				for idh in history:
					if idh is not None:
						id_list.append(idh.id)
			# print(id_list)
			for item in self.memory_bank:
				repeated = False
				if item.id in id_list:
					repeated = True
					contributed_items.append(item.id)
				history.append(item)
				freshness_score = self.__calculate_freshness_score(history, n, item)
				nonmonotonousness_score = weight_nonMon * self.__calculate_nonmonotonousness_score(
					history, n, item, repeated
				)
				current_item_score = 0
				coherence_score = self.__calculate_coherence_score(history, n, item)

				current_item_score = coherence_score + freshness_score + nonmonotonousness_score

				epsilon = 0.01
				preference_score = 0
				# best_ranked = item

				for i in item.subjects:
					preference_score += 1 - (self.preferences.index(i) / len(self.preferences))
				preference_score = preference_score / len(item.subjects)

				if current_item_score > best_score:
					best_score = current_item_score
					best_item = item

				elif abs(current_item_score - best_score) < epsilon:
					if best_item is not None and current_item_score + preference_score > best_score:
						best_score = current_item_score
						best_item = item

				history.pop(-1)

		item = best_item
		return best_item
