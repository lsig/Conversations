from collections import Counter

from models.player import GameContext, Item, Player, PlayerSnapshot

# import uuid
# import random


class Player6(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		super().__init__(snapshot, ctx)

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

	def __calculate_preference_score(self, current_item: Item):
		item_score = 0.0
		preferences = self.preferences
		if current_item is None:
			return item_score

		bonuses = [
			1 - preferences.index(s) / len(preferences)
			for s in current_item.subjects
			if s in preferences
		]
		if bonuses:
			item_score += sum(bonuses) / len(bonuses)

		return item_score

	def __calculate_individual_score(self, current_item: Item) -> float:
		return current_item.importance

	def propose_item(self, history: list[Item]) -> Item | None:
		weight_nonMon = 2.0
		best_item: Item = None
		best_score = -0.1
		n = len(history)

		if n == 0:
			try:
				if not self.memory_bank:
					return None

				def subj_pref(s: str) -> float:
					try:
						return 1.0 - (self.preferences.index(s) / len(self.preferences))
					except (ValueError, ZeroDivisionError):
						return 0.0

				def item_pref(it) -> float:
					subs = getattr(it, 'subjects', []) or []
					if not subs:
						return -1.0
					return sum(subj_pref(s) for s in subs) / len(subs)

				return max(
					self.memory_bank, key=lambda it: (item_pref(it), getattr(it, 'importance', 0.0))
				)

			except Exception:
				return self.memory_bank[-1]

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
