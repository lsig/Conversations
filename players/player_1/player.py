from collections import Counter
from uuid import UUID

from models.player import GameContext, Item, Player, PlayerSnapshot


class Player1(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		super().__init__(snapshot, ctx)

		self.subj_pref_ranking = {
			subject: snapshot.preferences.index(subject) for subject in snapshot.preferences
		}

		self.used_items: set[UUID] = set()

		# Adding dynamic playing style where we set the weights for coherence, importance and preference
		# based on the game context
		self.w_coh, self.w_imp, self.w_pref, self.w_nonmon, self.w_fresh = (
			self._init_dynamic_weights(ctx, snapshot)
		)
		self.ctx = ctx
		# Print Player 1 ID and wait for input
		# print(f"Player 1 ID: {self.id}")
		# input("Press Enter to continue...")

	def propose_item(self, history: list[Item]) -> Item | None:
		# print('\nCurrent Memory Bank: ', self.memory_bank)
		# print('\nConversation History: ', history)

		# If history length is 0, return the first item from preferred sort ( Has the highest Importance)
		if len(history) == 0:
			memory_bank_imp = importance_sort(self.memory_bank)
			return memory_bank_imp[0] if memory_bank_imp else None

		# This Checks Repitition so we dont repeat any item that has already been said in the history, returns a filtered memory bank
		self._update_used_items(history)
		filtered_memory_bank = check_repetition(self.memory_bank, self.used_items)
		# print('\nCurrent Memory Bank: ', len(self.memory_bank))
		# print('\nFiltered Memory Bank: ', len(filtered_memory_bank))

		# Return None if there are no valid items to propose
		if len(filtered_memory_bank) == 0:
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
		nonmonotonousness_scores = {
			item.id: score_nonmonotonousness(item, history) for item in filtered_memory_bank
		}
		freshness_scores = {
			item.id: score_freshness(item, history) for item in filtered_memory_bank
		}

		# Checking for if it is a pause turn for the weighting system
		if history[-1] is None:  # Last move was a pause
			# After a pause, we freshness to be weighted higher to take advantage of the opportunity
			self.w_coh, self.w_imp, self.w_pref, self.w_nonmon, self.w_fresh = (
				0.0,
				0.1,
				0.1,
				0.0,
				0.8,
			)

		best_item, best_now, weighted_scores = choose_item(
			filtered_memory_bank,
			coherence_scores,
			importance_scores,
			preference_scores,
			nonmonotonousness_scores,
			freshness_scores,
			weights=(self.w_coh, self.w_imp, self.w_pref, self.w_nonmon, self.w_fresh),
		)

		if best_item is None:
			return None

		# print("\nWeighted Item Scores:", max(weighted_scores.values(), default=None))

		# Decide to pause or speak
		if should_pause(
			weighted_scores,
			history,
			self.ctx.conversation_length,
			best_now,
			self.ctx.number_of_players,
		):
			# print('Decided to Pause')
			return None  # pause

		return best_item

	def _update_used_items(self, history: list[Item]) -> None:
		# Update the used_items set with items from history
		# if the item is None, it should not be added to the used_items set

		self.used_items.update(item.id for item in history if item is not None)

	def _init_dynamic_weights(
		self, ctx: GameContext, snapshot: PlayerSnapshot
	) -> tuple[float, float, float]:
		P = ctx.number_of_players
		L = ctx.conversation_length
		B = len(snapshot.memory_bank)

		# Base Weights
		w_coh, w_imp, w_pref, w_nonmon, w_fresh = 0.4, 0.3, 0.2, 0.1, 0.0

		# Length of Conversation
		if L <= 12:
			# short: focus importance
			w_coh, w_imp, w_pref, w_nonmon, w_fresh = 0.3, 0.45, 0.2, 0.05, 0.0
		elif L >= 31:
			# long: focus coherence even more strongly
			w_coh, w_imp, w_pref, w_nonmon, w_fresh = 0.5, 0.2, 0.15, 0.15, 0.0

		# Player Size
		if P <= 3:
			# small: More control, nudge coherence
			w_coh += 0.05
			w_imp -= 0.05
		elif P >= 6:
			# large: Less control, bank importance more heavily and cut preference
			w_coh -= 0.1
			w_imp += 0.1
			w_pref = max(w_pref - 0.05, 0.1)

		# Inventory Length
		if B <= 8:
			# conservative, focus coherence
			w_coh += 0.05
			w_imp -= 0.05
		elif B >= 16:
			# Less Conservative, focus importance
			w_imp += 0.05
			w_coh -= 0.05

		# clamp to [0,1] and softly renormalize to keep sum≈1
		w_coh = max(0.0, min(1.0, w_coh))
		w_imp = max(0.0, min(1.0, w_imp))
		w_pref = max(0.0, min(1.0, w_pref))
		w_nonmon = max(0.0, min(1.0, w_nonmon))
		w_fresh = max(0.0, min(1.0, w_fresh))

		total = w_coh + w_imp + w_pref + w_nonmon + w_fresh
		if total > 0:
			w_coh, w_imp, w_pref, w_nonmon, w_fresh = (
				w_coh / total,
				w_imp / total,
				w_pref / total,
				w_nonmon / total,
				w_fresh / total,
			)

		# Cap preference weight depending on conversation length
		if L <= 12 and w_pref > 0.18:
			w_pref = 0.18
		elif L >= 31 and w_pref > 0.15:
			w_pref = 0.15

		# Renormalize after capping preference
		total = w_coh + w_imp + w_pref + w_nonmon + w_fresh
		if total > 0:
			w_coh, w_imp, w_pref, w_nonmon, w_fresh = (
				w_coh / total,
				w_imp / total,
				w_pref / total,
				w_nonmon / total,
				w_fresh / total,
			)

		return (w_coh, w_imp, w_pref, w_nonmon, w_fresh)


# Helper Functions #


def check_repetition(memory_bank: list[Item], used_items: set[UUID]) -> list[Item]:
	# Filter out items with IDs already in the used_items set
	return [item for item in memory_bank if item.id not in used_items]


def coherence_check(current_item: Item, history: list[Item]) -> float:
	# Check the last 3 items in history (or fewer if history is shorter)
	if current_item is None:
		return 0.0

	recent_history = []
	start_idx = max(0, len(history) - 3)

	for i in range(len(history) - 1, start_idx - 1, -1):
		item = history[i]
		if item is None:
			break
		recent_history.append(item)

	# Count occurrences of each subject in the recent history
	subject_count = Counter()
	for item in recent_history:  # won't be None
		subject_count.update(item.subjects)

	# See if all subjects in the current item are appear once or twice in the history
	subjects = current_item.subjects
	counts = [subject_count.get(s, 0) for s in subjects]

	if any(c == 0 for c in counts):
		return 0.0

	if all(c >= 2 for c in counts):
		return 1.0  # awarding full point for 2 mentions

	if all(c >= 1 for c in counts):
		return 0.5

	return 0.0

	# Debugging prints
	# print("\nCurrent Item Subjects:", current_item.subjects)
	# print("History Length:", len(history))
	# print("Recent History:", [item.subjects for item in recent_history])
	# print("Subject Count:", subject_count)
	# print("Coherence Score Before Normalization:", coherence_score)
	# print("Coherence Score After Normalization:", coherence_score / len(current_item.subjects) if current_item.subjects else 0.0)
	# print("Number of Subjects in Current Item:", len(current_item.subjects))


def score_freshness(current_item: Item, history: list[Item]) -> float:
	recent_history = history[-6:-2]  # 5 items before current turn
	novel_subjects = 0

	# Check for if we have to account for pauses in the recent history
	history_subjects = set()
	for item in recent_history:
		if item is not None:
			history_subjects.update(item.subjects)

	for subj in current_item.subjects:
		if subj not in history_subjects:
			novel_subjects += 1

	# Should the score be 0.5 or maybe 0.75 for one novel subject?
	if novel_subjects == 0:
		return 0.0
	elif novel_subjects == 1:
		return 0.5
	else:  # novel_subjects = 2
		return 1.0


def score_nonmonotonousness(current_item: Item, history: list[Item]) -> float:
	if current_item is None:
		return 0.0

	recent_history = history[-3:]
	penalty = 0

	for subj in current_item.subjects:
		if all(
			prev_item is not None and any(prev_subj == subj for prev_subj in prev_item.subjects)
			for prev_item in recent_history
		):
			penalty -= 1

	if current_item in history:
		penalty -= 1

	max_penalty = len(current_item.subjects) + 1 if current_item.subjects else 1

	score = 1.0 - (penalty / max_penalty)
	return max(0.0, score)


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
	item_id,
	coherence_scores,
	importance_scores,
	preference_scores,
	nonmonotonousness_scores,
	freshness_scores,
	weights,
):
	w1, w2, w3, w4, w5 = weights
	coherence = coherence_scores.get(item_id, 0.0)
	importance = importance_scores.get(item_id, 0.0)
	preference = preference_scores.get(item_id, 0.0)
	nonmonotonousness = nonmonotonousness_scores.get(item_id, 0.0)
	freshness = freshness_scores.get(item_id, 0.0)

	return (
		w1 * coherence + w2 * importance + w3 * preference + w4 * nonmonotonousness + w5 * freshness
	)


def choose_item(
	memory_bank: list[Item],
	coherence_scores: dict[UUID, float],
	importance_scores: dict[UUID, float],
	preference_scores: dict[UUID, float],
	nonmonotonousness_scores: dict[UUID, float],
	freshness_scores: dict[UUID, float],
	weights: tuple[float, float, float, float],
):
	weighted_scores = {
		item.id: calculate_weighted_score(
			item.id,
			coherence_scores,
			importance_scores,
			preference_scores,
			nonmonotonousness_scores,
			freshness_scores,
			weights,
		)
		for item in memory_bank
	}
	if not weighted_scores:
		return None

	# Best candidate now
	best_item_id, best_now = max(weighted_scores.items(), key=lambda kv: kv[1])
	best_item = next((it for it in memory_bank if it.id == best_item_id), None)

	# Return Best Item and its score, weighted scores for pause decision
	return best_item, best_now, weighted_scores

	# Takes in the total memory bank and scores each item based on whatever weighting system we have
	# Actually should make this a function in the class so it can have access to the contributed items/memory bank
	# Should automatically score things that were already in the contributed items a 0

	# As its scored, add it to a set thats sorted by the score. Return Set


##################################################
# Helper functions for pause decisions
##################################################


def count_consecutive_pauses(history: list[Item]) -> int:
	# Check only the two most recent moves for consecutive pauses
	cnt = 0
	for it in reversed(history[-2:]):  # Limit to the last two moves
		if it is None:
			cnt += 1
		else:
			break
	return cnt


def should_pause(
	weighted_scores: dict[UUID, float],
	history: list[Item],
	conversation_length: int,
	best_now: float,
	number_of_players: int,
) -> bool:
	"""
	Compute a dynamic threshold for speaking.
	Return True if we should pause (i.e., best_now < threshold).
	"""
	# Set a base threshold by conversation length
	# Short games: lower ceilings on weighted scores = lower threshold.
	# Long games: higher ceilings = higher threshold.

	# REDO THIS TO MAYBE DECIDE A STARTING THRESHOLD BASED ON THE AVG WEIGHTED SCORES
	threshold = base_threshold(weighted_scores)

	# Check and see the last two moves were pauses for risk of termination
	cons_pauses = count_consecutive_pauses(history)
	# print(f'Consecutive Pauses: {cons_pauses}')
	if cons_pauses >= 2:
		# Pausing risks immediate termination; lower threshold so we prefer to speak
		threshold -= 0.30
	elif cons_pauses == 1:
		threshold -= 0.15

	# See the number of turns left; fewer turns left means we should lower threshold and speak more
	turns_so_far = sum(1 for it in history if it is not None or it is None)  # history length
	turns_left = max(0, conversation_length - turns_so_far)
	# print(f'Turns Left: {turns_left}')
	if turns_left <= 3:
		threshold -= 0.10
	elif turns_left <= 6:
		threshold -= 0.05

	# THIS MIGHT NEEd TWEAKED IM NOT TOO SURE ABOUT IT
	if number_of_players >= 6:
		threshold -= 0.05
	elif number_of_players <= 3:
		threshold += 0.05

	# ensure threshold is within reasonable bounds
	threshold = max(0.35, min(0.90, threshold))
	# print(
	# 	f'Pause Decision: best_now={best_now:.3f} vs threshold={threshold:.3f} (cons_pauses={cons_pauses}, turns_left={turns_left}'
	# )
	return best_now < threshold


def base_threshold(weighted_scores) -> float:
	"""
	Set the *base* speak/pause threshold as the average of the top 3 weighted scores.
	"""
	if not weighted_scores:
		return 0.5  # Default threshold if no scores are available

	top_scores = sorted(weighted_scores.values(), reverse=True)[:3]
	average_score = sum(top_scores) / len(top_scores)
	return average_score
