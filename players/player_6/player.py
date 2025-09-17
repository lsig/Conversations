from collections import Counter

from models.player import GameContext, Item, Player, PlayerSnapshot

# import uuid
# import random


class Player6(Player):
	def _init_(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super()._init_(snapshot, ctx)

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
		best_item: Item = None
		best_score = 0
		n = len(history)
		id_list = []
		if history is not None:
			for idh in history:
				if idh is not None:
					id_list.append(idh.id)
		# print(id_list)
		for item in self.memory_bank:
			repeated = False
			if item.id in id_list:
				repeated = True
			history.append(item)
			freshness_score = self.__calculate_freshness_score(history, n, item)
			nonmonotonousness_score = self.__calculate_nonmonotonousness_score(
				history, n, item, repeated
			)
			current_item_score = 0
			coherence_score = self.__calculate_coherence_score(history, n, item)

			# print('*'*20)
			# print(f"ITEM: {item}")
			# print(f"INDIVIDUAL SCORE: {individual_score}")
			# print(f"FRESHNESS SCORE: {freshness_score}")
			# print(f"NONMONO SCORE: {nonmonotonousness_score}")
			# print(f"TOTAL COHERENCE SCORE: {coherence_score}")
			# print('*'*20)

			current_item_score = coherence_score + freshness_score + nonmonotonousness_score

			epsilon = 0.1
			preference_score = 0
			for i in item.subjects:
				preference_score += 1 - (self.preferences.index(i) / len(self.preferences))
			preference_score = preference_score / len(item.subjects)

			if current_item_score > best_score:
				best_score = current_item_score
				best_item = item

			elif abs(current_item_score - best_score) > epsilon:
				if best_item is not None and current_item_score + preference_score > best_score:
					best_score = current_item_score
					best_item = item

			history.pop(-1)

		# print('%'*20)
		item = best_item
		repeated = False
		# print(f"BEST_ITEM: {item}")
		if item is not None:
			if item.id in id_list:
				repeated = True
			history.append(item)
			#individual_score = 0
			freshness_score = self.__calculate_freshness_score(history, n, item)
			nonmonotonousness_score = self.__calculate_nonmonotonousness_score(
				history, n, item, repeated
			)
			current_item_score = 0
			coherence_score = self.__calculate_coherence_score(history, n, item)

			# print(f"INDIVIDUAL SCORE: {individual_score}")
			# print(f"FRESHNESS SCORE: {freshness_score}")
			# print(f"NONMONO SCORE: {nonmonotonousness_score}")
			# print(f"TOTAL COHERENCE SCORE: {coherence_score}")
			history.pop(-1)
			# print('%'*20)
		return best_item
