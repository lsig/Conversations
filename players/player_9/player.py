from models.player import Item, Player, PlayerSnapshot

#test
class Player9(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	def propose_item(self, history: list[Item]) -> Item | None:
		item_scores = []

		# calculate score for each item
		for item in self.memory_bank:
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

			item_scores.append(
				(
					item,
					total_bonus,
					coherence_bonus,
					importance_bonus,
					freshness_bonus,
					nonmonotonousness_bonus,
					individual_bonus,
				)
			)

		item_scores.sort(key=lambda x: x[1], reverse=True)
		return item_scores[0][0]
