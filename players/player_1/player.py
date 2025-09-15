from uuid import UUID

from models.player import Item, Player, PlayerSnapshot, GameContext
from collections import Counter


class Player1(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)

		self.subj_pref_ranking = {
			subject: snapshot.preferences.index(subject) for subject in snapshot.preferences
		}
		# player snapshot includes preferences and memory bank of items to contribute

	def propose_item(self, history: list[Item]) -> Item | None:
		#print('\nCurrent Memory Bank: ', self.memory_bank)
		#print('\nConversation History: ', history)

		# If history length is 0, return the first item from preferred sort ( Has the highest Importance)
		if len(history) == 0:
			memory_bank_imp = importance_sort(self.memory_bank)
			# print("Sorted by Important: ", memory_bank_imp)
			# input("Press Enter to continue... Importance Sort Complete")
			return memory_bank_imp[0] if memory_bank_imp else None

		# This Checks Repitition so we dont repeat any item that has already been said in the history, returns a filtered memory bank
		filtered_memory_bank = check_repetition(history, self.used_items, self.memory_bank)
		#print('\nFiltered Memory Bank: ', filtered_memory_bank)

		# Return None if there are no valid items to propose
		# This can be changed in future just incase we run out of things to say and have to repeat. Not sure if this is possible
		if len(filtered_memory_bank) == 0:
			#print('No valid items to propose after filtering')
			# Use importance score if no items are left after filtering
			memory_bank_imp = importance_sort(self.memory_bank)
			return memory_bank_imp[0] if memory_bank_imp else None

		coherence_scores = {
			item.id: coherence_check(item, history) for item in filtered_memory_bank
		}
		importance_scores = {item.id: item.importance for item in filtered_memory_bank}
		preference_scores = {
			item.id: score_item_preference(item.subjects, self.subj_pref_ranking)
			for item in filtered_memory_bank
		}

		# Sort memory bank based on coherence and importance_sort
		# memory_bank_co = coherence_sort(filtered_memory_bank, history)
		# print("Sorted by Coherence: ", memory_bank_co)
		# input("Press Enter to continue... Coherence Sort Complete")

		# memory_bank_imp = importance_sort(filtered_memory_bank)

		# memory_bank_pref = self.preference_sort(filtered_memory_bank)

		# weighted_list = self.weight_matrix(filtered_memory_bank, memory_bank_co, memory_bank_imp, memory_bank_pref)
		item = choose_item(
			filtered_memory_bank, coherence_scores, importance_scores, preference_scores
		)

		if item:
			return item
		else:
			return None

	# def preference_sort (self, memory_bank: list[Item]):
	# 	#Returns a list of the memory bank based on preference sorting
	# 	pref_sorted_items = sorted(memory_bank, key=lambda x: self.custom_pref_sort(x.subjects))
	# 	return pref_sorted_items

	# Personal Variables
	# last_suggestion: Item
	used_items: set[UUID] = set()


# Helper Functions #


def check_repetition(history: list[Item], used_items, memory_bank) -> list[Item]:
	# Update the proposed items set with items from history
	used_items.update(item.id for item in history)

	# Filter out items with IDs already in the proposed items set
	return [item for item in memory_bank if item.id not in used_items]


def coherence_check(current_item: Item, history: list[Item]) -> float:
	# Check the last 3 items in history (or fewer if history is shorter)
	recent_history = history[-3:]
	coherence_score = 0

	# Count occurrences of each subject in the recent history
	subject_count = {}
	for item in recent_history:
		for subject in item.subjects:
			subject_count[subject] = subject_count.get(subject, 0) + 1

	has_missing = False
	all_twice = True

	# See if all subjects in the current item are appear once or twice in the history
	for subject in current_item.subjects:
		count = subject_count.get(subject, 0)

		if count != 2:
			if count == 0:
				has_missing = True
			else:
				all_twice = False
			break

		# if subject_count.get(subject, 0) in [1, 2]:
		# 	coherence_score += 1

	if has_missing:
		coherence_score -= 1  # penalize if subject is missing from prior context. can refine later
	elif all_twice:
		coherence_score += 1  # reward if all subjects are mentioned exactly twice in prior context
	else:
		coherence_score = 0

	# Debugging prints
	# print("\nCurrent Item Subjects:", current_item.subjects)
	# print("History Length:", len(history))
	# print("Recent History:", [item.subjects for item in recent_history])
	# print("Subject Count:", subject_count)
	# print("Coherence Score Before Normalization:", coherence_score)
	# print("Coherence Score After Normalization:", coherence_score / len(current_item.subjects) if current_item.subjects else 0.0)
	# print("Number of Subjects in Current Item:", len(current_item.subjects))

	# This should return a score between 0 and 1 (Not exactly the 0 .5 1 you wanted can be changed later)
	# return coherence_score / len(current_item.subjects) if current_item.subjects else 0.0

	return (coherence_score + 1) / 2


def coherence_sort(memory_bank: list[Item], history: list[Item]) -> list[Item]:
	# Sort the memory bank based on coherence scores in descending order
	# use a lambda on each item to check coherence score
	sorted_memory = sorted(
		memory_bank, key=lambda item: coherence_check(item, history), reverse=True
	)
	return sorted_memory


def importance_sort(memory_bank: list[Item]) -> list[Item]:
	# Sort the memory bank based on the importance attribute in descending order
	return sorted(memory_bank, key=lambda item: item.importance, reverse=True)


def score_item_preference(subjects, subj_pref_ranking):
	if not subjects:
		return 0.0

	S_length = len(subj_pref_ranking)
	bonuses = [
		1 - subj_pref_ranking.get(subject, S_length) / S_length for subject in subjects
	]  # bonus is already a preference score of sorts
	return sum(bonuses) / len(bonuses)


def calculate_weighted_score(
	item_id, coherence_scores, importance_scores, preference_scores, weights
):
	w1, w2, w3 = weights
	coherence = coherence_scores.get(item_id, 0.0)
	importance = importance_scores.get(item_id, 0.0)
	preference = preference_scores.get(item_id, 0.0)

	return w1 * coherence + w2 * importance + w3 * preference


def choose_item(
	memory_bank: list[Item],
	coherence_scores: dict[UUID, float],
	importance_scores: dict[UUID, float],
	preference_scores: dict[UUID, float],
):
	w1 = 0.4
	w2 = 0.3
	w3 = 0.3

	# tune weights somehow

	weights = w1, w2, w3

	weighted_item_scores = {
		item: calculate_weighted_score(
			item.id, coherence_scores, importance_scores, preference_scores, weights
		)
		for item in memory_bank
	}

	sorted_items = sorted(weighted_item_scores.items(), key=lambda item: item[1], reverse=True)
	return sorted_items[0][0] if sorted_items else None

	# Takes in the total memory bank and scores each item based on whatever weighting system we have
	# Actually should make this a function in the class so it can have access to the contributed items/memory bank
	# Should automatically score things that were already in the contributed items a 0

	# As its scored, add it to a set thats sorted by the score. Return Set
