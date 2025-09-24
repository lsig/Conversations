from collections import Counter, defaultdict
from uuid import UUID

from models.player import GameContext, Item, Player, PlayerSnapshot


class Player1(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		super().__init__(snapshot, ctx)

		self.subj_pref_ranking = {
			subject: snapshot.preferences.index(subject) for subject in snapshot.preferences
		}

		self.used_items: set[UUID] = set()
		self.snapshot = snapshot
		self.threshold = 0.5  # Default threshold for pause decision

		# Adding dynamic playing style where we set the weights for coherence, importance and preference
		# based on the game context
		self.w_coh, self.w_imp, self.w_pref, self.w_nonmon, self.w_fresh = (
			self._init_dynamic_weights(ctx, snapshot)
		)
		self.ctx = ctx

		#  track information about other players

		self.player_subjects = defaultdict(Counter)
		self.player_actions = defaultdict(list)
		self.player_turns = Counter()
		self.player_coherence_contributions = defaultdict(float)
		self.player_coherence_fraction = defaultdict(float)

		# Print Player 1 ID and wait for input
		# print(f"Player 1 ID: {self.id}")
		# input("Press Enter to continue...")

	def propose_item(self, history: list[Item]) -> Item | None:
		# print('\nConversation History: ', history)

		#  update metadata
		new_item_tups = self.get_items_since_my_last_turn(history)

		for item_tup in new_item_tups:
			self.update_player_data(item_tup, history)  # must happen before updating used items

		# If history length is 0, return the first item from preferred sort ( Has the highest Importance)
		# if len(history) == 0:
		# 	memory_bank_imp = importance_sort(self.memory_bank)
		# 	# return memory_bank_imp[0] if memory_bank_imp else None

		# If the last item in history is in our memory bank, we add it to our contributed items
		if (
			len(history) != 0
			and history[-1] is not None
			and history[-1] in self.memory_bank
			and history[-1] not in self.contributed_items
		):
			self.contributed_items.append(history[-1])

		# This Checks Repitition so we dont repeat any item that has already been said in the history, returns a filtered memory bank
		self._update_used_items(history)

		filtered_memory_bank = check_repetition(self.memory_bank, self.used_items)
		# print('\nCurrent Memory Bank: ', len(self.memory_bank))
		# print('\nFiltered Memory Bank: ', len(filtered_memory_bank))

		# Return None if there are no valid items to propose
		if len(filtered_memory_bank) == 0:
			return None

		# Dynamically adjust weights based on game context and recent history
		(
			self.w_coh,
			self.w_imp,
			self.w_pref,
			self.w_nonmon,
			self.w_fresh,
			is_fresh_turn,
			is_monotonous_turn,
		) = self.dynamic_adjustment(history, self.ctx, self.snapshot)

		# print("fresh turn: ", is_fresh_turn, "monotonous turn: ", is_monotonous_turn)

		# SCORE CALCULATIONS FOR EACH ITEM
		coherence_scores = {
			item.id: score_coherence(self, item, history, filtered_memory_bank)
			for item in filtered_memory_bank
		}

		importance_scores = {
			item.id: (item.importance, item.importance) for item in filtered_memory_bank
		}
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

		score_sources = {
			'coherence': coherence_scores,
			'importance': importance_scores,
			'preference': preference_scores,
			'nonmonotonousness': nonmonotonousness_scores,
			'freshness': freshness_scores,
		}

		average_past_7 = average_score_last_n(filtered_memory_bank, history, 7, self)
		# print("Average Last 7 Final Scores: ", average_past_7)
		average_past_3 = average_score_last_n(filtered_memory_bank, history, 3, self)
		# print("Average Last 3 Final Scores: ", average_past_3)
		# print("Current Threshold: ", self.threshold)
		if average_past_7 != 0.0:
			average_change = average_past_3 - average_past_7
			self.threshold = 0.5 + average_change / 2

		# if (average_past_n != 0.0) and (len(history) >= 7 ):
		# self.threshold = max(0.25, .25 + average_past_n/2)

		best_item, best_now, weighted_scores = choose_item(
			self,
			filtered_memory_bank,
			score_sources,
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
			return best_item  # pause

		return best_item

	def _update_used_items(self, history: list[Item]) -> None:
		# Update the used_items set with items from history
		# Create a set of IDs of items in the player's memory bank
		# if the item is None, it should not be added to the used_items set
		# memory_ids = {item.id for item in self.memory_bank}
		self.used_items.update(item.id for item in history if item is not None)

	def _init_dynamic_weights(
		self, ctx: GameContext, snapshot: PlayerSnapshot
	) -> tuple[float, float, float, float, float]:
		P = ctx.number_of_players
		L = ctx.conversation_length
		B = len(snapshot.memory_bank) - len(self.contributed_items)

		# Ratio of Coverage
		R = 0
		if B > 0:
			R = L / (P * B)

		# Base Weights
		w_coh = 1.5 / ((2 * R) ** 2 + 1)
		w_imp = 1 / (R + 1)
		w_pref = 1 / (R + 1) * abs(R - 1)
		w_nonmon = 0
		w_fresh = 0

		# Normalize Weights
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

	def dynamic_adjustment(self, history: list[Item], ctx: GameContext, snapshot: PlayerSnapshot):
		# Adjust weights based on game context
		P = ctx.number_of_players
		L = ctx.conversation_length - len(history)
		B = len(snapshot.memory_bank) - len(self.contributed_items)
		is_fresh_turn = False
		is_monotonous_turn = False

		# ADD IN SOMETHING THAT CHANGES THE SCALED VS RAW SCORES

		# Ratio of Coverage
		R = 0
		if B > 0:
			R = L / (P * B)

		# Base Weights
		w_coh = 1.5 / ((2 * R) ** 2 + 1)
		w_imp = 1 / (R + 1)
		w_pref = 1 / (R + 1) * abs(R - 1)
		w_nonmon = 0
		w_fresh = 0

		# Checking for if it is a pause turn for the weighting system
		if len(history) != 0 and history[-1] is None:  # Last move was a pause
			# After a pause, we freshness to be weighted higher to take advantage of the opportunity
			is_fresh_turn = True
			w_coh, w_imp, w_pref, w_nonmon, w_fresh = (
				0.0,
				0.1,
				0.1,
				0.0,
				0.8,
			)

		# Checking for monotonousness in the recent history (only time we use the weight)
		subj_counts, top_freq, unique, seen_recent = recent_subject_stats(history, 3)
		if top_freq == 3:
			is_monotonous_turn = True
			w_coh, w_imp, w_pref, w_nonmon, w_fresh = (
				0.05,
				0.05,
				0.2,
				0.7,
				0.0,
			)

		# Normalize Weights
		total = w_coh + w_imp + w_pref + w_nonmon + w_fresh
		if total > 0:
			w_coh, w_imp, w_pref, w_nonmon, w_fresh = (
				w_coh / total,
				w_imp / total,
				w_pref / total,
				w_nonmon / total,
				w_fresh / total,
			)
		# print("Player ID: ", self.id)
		# print("contributed items: ", (self.contributed_items))
		# print("Coverage Ratio", R, "Length of Conversation Remaining: ", L, " | Number of Players: ", P, " | Items Remaining: ", B)
		# print(f'Weights: Coherence: {w_coh}, Importance: {w_imp}, Preference: {w_pref}, Nonmonotonousness: {w_nonmon}, Freshness: {w_fresh}')
		return (w_coh, w_imp, w_pref, w_nonmon, w_fresh, is_fresh_turn, is_monotonous_turn)

	def get_items_since_my_last_turn(self, history: list[Item]):
		for i in range(len(history) - 1, -1, -1):
			if (
				history[i] is not None and history[i].player_id == self.id
			):  # look at every item since the last time I spoke
				#  pauses are ignored
				item_idx_tups = []
				j = i + 1
				while j < len(history):
					past_item = history[j]
					if past_item not in self.used_items:
						item_idx_tups.append((j, past_item))
					j += 1
				return item_idx_tups  # returns list of tuples of (idx, item) for most recent items
		#  this way, we can easily get the idx that the item happened at without searching for it again
		return [
			(j, item) for j, item in enumerate(history)
		]  # if we haven't spoken, return whole history

	def update_player_data(self, item_tup: tuple[int, Item] | None, history):
		_, item = item_tup

		if item is None:
			return

		player_id = item.player_id
		self.player_turns[player_id] += 1
		self.player_actions[player_id].append(item)  # keep track of each thing the player has said

		for subject in item.subjects:
			self.player_subjects[player_id][subject] += (
				1  # keep track of how many times they've mentioned each subject
			)
			#  use as an indication of preference

		if self.item_knowingly_coherent(item_tup, history):
			# given the 3 before, did they choose to continue the coherence or not?
			# that gives an idea of whether they'll continue coherence if we say something coherent
			self.player_coherence_contributions[player_id] += 1

		total = len(self.player_actions[player_id])
		coh_count = self.player_coherence_contributions.get(
			player_id, 0
		)  # how many times have they contributed to coherence?

		coherence_fraction = (
			coh_count / total if total > 0 else 0
		)  # out of their contributed items, how many were continuing a coherence chain?
		self.player_coherence_fraction[player_id] = coherence_fraction

	#########################################################
	#### Category: Helper Methods for Coherence Score #####
	#########################################################

	def expected_planning_bonus_lookahead(
		self,
		current_speaker_id,
		player_turns,
		subjects,
		current_item,
		filtered_memory_bank,
		missing_subjects,
	):
		dist = {current_speaker_id: 1.0}
		total_expected_bonus = 0.0

		for _ in range(3):
			next_dist = defaultdict(float)  # prob dist for the next speaker
			for speaker, prob in dist.items():  # go through all possible next speakers
				updated_counts = player_turns.copy()  #  turns for each player
				updated_counts[speaker] += 1  # add to that speaker bc they just spoke
				next_probs = self.get_next_player_probs(
					speaker, updated_counts
				)  # get next speakers and their probabilities

				for (
					next_speaker,
					next_prob,
				) in next_probs.items():  # for each possible next speaker,
					bonus = self.compute_planning_bonus_for_speaker(
						next_speaker, subjects, current_item
					)
					mention_prob = self.expected_subject_mention_coverage(
						missing_subjects, next_speaker
					)  # how likely are they to mention a missing subject?

					num_subjects = max(1, len(subjects))
					num_missing = len(missing_subjects)
					missing_frac = num_missing / num_subjects
					weighted_bonus = bonus * (
						1.0 - 0.5 * missing_frac + 0.5 * missing_frac * mention_prob
					)
					#  adjusting for the number of missing subjects. so this depends on both # missing subjects and
					#  mention probability
					#  lowest possible is still 0.5. don't want bonus to not count at all, just bc of low mention probability
					total_expected_bonus += prob * next_prob * weighted_bonus
					# add to the bonus, the chance that we get to this speaker * the chance that we get to the next speaker * how good of a move they're likely to make
					#  * the chance they mention the missing subject
					next_dist[next_speaker] += (
						prob * next_prob
					)  # prob that next speaker will speak in next round
			dist = next_dist

		max_possible_bonus = 3 * 2.0
		return min(total_expected_bonus / max_possible_bonus, 1.0)  # scale it down from 0 to 1

	def compute_planning_bonus_for_speaker(
		self, speaker_id: UUID, subjects: list[str], current_item: Item
	) -> float:
		#  if the speaker is me, we can directly tell whether we can finish the thread
		self_coherence_bonus = 0.0
		if speaker_id == self.id:
			_, subject_preference_bonus = score_item_preference(subjects, self.subj_pref_ranking)
			for subj in subjects:
				if any(
					subj in item.subjects
					and item.id
					!= current_item.id  # if we have something that can finish the thread
					for item in self.memory_bank
				):
					self_coherence_bonus = (
						0.5  # could have bonus scale to # followups available. could be monotonous!
					)
					break

			total_bonus = subject_preference_bonus + self_coherence_bonus
		else:
			favorite_player_subject_bonus = 0.0
			# how often do they mention this subject? estimate a "preference" of sorts

			subject_mentions = self.player_subjects.get(speaker_id, {})
			total_mentions = sum(subject_mentions.values())
			if total_mentions > 0:
				for subj in subjects:
					freq = subject_mentions.get(subj, 0)
					favorite_player_subject_bonus += freq / total_mentions

			coherence_frac = self.player_coherence_fraction.get(speaker_id, 0.0)
			expected_coherence_fraction_bonus = min(coherence_frac, 1.0) * 0.5  # scale it down

			total_bonus = favorite_player_subject_bonus + expected_coherence_fraction_bonus

		return total_bonus

	def expected_subject_mention_coverage(
		self, subjects_needed: list[str], speaker_id: UUID
	) -> float:
		subject_mentions = self.player_subjects.get(speaker_id, {})
		total_mentions = sum(subject_mentions.values())
		if total_mentions == 0:
			return 0.0

		prob_not_mentioned = 1.0
		for subj in subjects_needed:
			freq = subject_mentions.get(subj, 0)
			p_mention = freq / total_mentions
			prob_not_mentioned *= 1.0 - p_mention

		prob_mention_any = (
			1.0 - prob_not_mentioned
		)  # getting rid of the repeats since items can have two subjects
		return prob_mention_any

	def get_next_player_probs(
		self, current_speaker_id: UUID, player_turns: dict[UUID, int]
	) -> dict[UUID, float]:
		if not player_turns:
			return {}

		other_counts = [count for _, count in player_turns.items()]
		if not other_counts:
			return {current_speaker_id: 1.0}
		min_contrib = min(other_counts)

		lowest_contributors = [pid for pid, count in player_turns.items() if count == min_contrib]

		num_lowest = len(lowest_contributors)

		probs = dict()

		probs[current_speaker_id] = 0.5

		if num_lowest > 0:
			share = 0.5 / num_lowest
			for pid in lowest_contributors:
				if pid not in probs:
					probs[pid] = 0.0
				probs[pid] += share
		return probs

	"""
	Determine whether item tried to be coherent with the previous 3 items.
	"""

	def item_knowingly_coherent(self, item_tup: tuple[int, Item], history: list[Item]) -> bool:
		item_history_idx, item = item_tup

		if item is None:
			return False

		back_count = 0
		i = item_history_idx - 1
		while i >= 0 and back_count < 3:
			prev_item = history[i]
			if prev_item is None:
				break
			if any(subj in prev_item.subjects for subj in item.subjects):
				return True
			back_count += 1
			i -= 1

		return False


# Helper Functions #


def recent_subject_stats(history: list[Item], window: int = 6):
	# Look back `window` turns (skipping None), return:
	# - subj_counts: Counter of subjects in the window
	# - top_freq:    max frequency of any subject (0 if none)
	# - unique:      number of unique subjects
	# - seen_recent: set of subjects observed
	recent = [it for it in history[-window:] if it is not None]
	subjects = [s for it in recent for s in it.subjects]

	subj_counts = Counter(subjects)
	top_freq = max(subj_counts.values()) if subj_counts else 0
	unique = len(subj_counts)
	return subj_counts, top_freq, unique, set(subjects)


##################################################
#### Category: Scoring and Sorting Functions #####
##################################################


def inventory_subjects(items: list[Item]) -> set[str]:
	# All subjects still available to play from the filtered memory bank.
	return {s for it in items for s in it.subjects}


def check_repetition(memory_bank: list[Item], used_items: set[UUID]) -> list[Item]:
	# Filter out items with IDs already in the used_items set
	return [item for item in memory_bank if item.id not in used_items]


def score_coherence(
	player: Player1, current_item: Item, history: list[Item], filtered_memory_bank
) -> float:
	if current_item is None:
		return 0.0, 0.0

	recent_history = []
	start_idx = max(0, len(history) - 3)
	for i in range(len(history) - 1, start_idx - 1, -1):
		item = history[i]
		if item is None:
			break
		recent_history.append(item)

	subject_count = Counter()
	for item in recent_history:
		subject_count.update(item.subjects)

	subjects = current_item.subjects
	counts = [subject_count.get(s, 0) for s in subjects]
	missing_subjects = [s for s, c in zip(subjects, counts, strict=False) if c < 2]

	#  cases to apply bonus:
	# - if item is 1 subject, and the previous context mentions that subject once
	# - if item is 2 subjects, and each subject has been mentioned once in the previous context
	# what is the expected value of the next speaker saying at least one of the subjects next? of saying both subjects?
	# this isn't a necessary condition for coherence, but it's all the info we can gather about whether the thread will be continued
	# or I guess the global leaning towards coherence int he overall conversation - that might add a bonus for the last two spots int the future context
	# - if item is 2 subjects, and one subject has been mentioned once and the other subject has been mentioned twice in the previous context,
	# what is the expected value fo the next speaker saying the missing subject next?
	# and maybe again take into account expected value based on the global leaning towards coherence in the overall conversation, for the last two spots in the future context

	min_turns_before_bonus = 10
	enough_history = len(history) >= min_turns_before_bonus

	apply_bonus = False
	coherence_uncertain = (
		enough_history
		and (len(counts) == 1 and counts[0] == 1)
		or (len(counts) == 2 and (counts == [1, 1] or (2 in counts and 1 in counts)))
	)
	if coherence_uncertain:
		apply_bonus = True

	#  raw score reflects degrees of overlap with the previous context

	if len(counts) == 1:
		if counts[0] == 0:
			raw_score = -1.0
			scaled_score = 0.0
		elif counts[0] == 1:
			raw_score = 0.0
			scaled_score = 0.5
		else:  # # counts[0] >= 2
			raw_score = 1.0
			scaled_score = 1.0

	elif len(counts) == 2:
		if counts[0] == 0 and counts[1] == 0:
			raw_score = -1.0
		elif (counts[0] == 1 and counts[1] == 0) or (counts[0] == 0 and counts[1] == 1):
			raw_score = 0.167
		elif counts[0] == 1 and counts[1] == 1:
			raw_score = 0.5
		elif (counts[0] == 2 and counts[1] == 0) or (counts[0] == 0 and counts[1] == 2):
			raw_score = 0.333
		elif (counts[0] == 2 and counts[1] == 1) or (counts[0] == 1 and counts[1] == 2):
			raw_score = 1.0
		else:
			raw_score = -1.0

	scaled_score = (raw_score + 1.0) / 2.0  # normalize from 0 to 1

	if apply_bonus:
		bonus = player.expected_planning_bonus_lookahead(
			current_speaker_id=current_item.player_id,
			player_turns=player.player_turns.copy(),
			subjects=subjects,
			current_item=current_item,
			filtered_memory_bank=filtered_memory_bank,
			missing_subjects=missing_subjects,
		)

		bonus_weight = 1.0 - scaled_score  # more bonus used if coherence is more uncertain
		scaled_score = min(scaled_score + bonus_weight * bonus, 1.0)

	return raw_score, scaled_score


def score_freshness(current_item: Item, history: list[Item]) -> float:
	if current_item is None:
		return 0.0

	if len(history) != 0 and history[-1] is not None:
		raw_score = 0.0
		scaled_score = 0.0
		# print(f"Freshness - Item ID: {current_item.id}, Raw Score: {raw_score}, Scaled Score: {scaled_score}")
		return raw_score, scaled_score

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
		raw_score = 0.0
		scaled_score = 0.0
		return raw_score, scaled_score
	elif novel_subjects == 1:
		raw_score = 1.0
		scaled_score = 0.5
	else:  # novel_subjects = 2
		raw_score = 2.0
		scaled_score = 1.0
	# print(f"Freshness - Item ID: {current_item.id}, Raw Score: {raw_score}, Scaled Score: {scaled_score}")
	return raw_score, scaled_score


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

	if current_item.id in {item.id for item in history if item is not None}:
		penalty -= 1

	raw_score = penalty

	max_penalty = len(current_item.subjects) if current_item.subjects else 1

	scaled_score = 1.0 + (penalty / max_penalty)  # higher scaled score is more nonmonotonous
	# print(f"Nonmonotonousness - Item ID: {current_item.id}, Raw Score: {raw_score}, Scaled Score: {scaled_score}")
	return raw_score, scaled_score


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
	raw_score = sum(bonuses) / len(bonuses)
	# print(f"Preference - Subjects: {subjects}, Raw Score: {raw_score}")

	scaled_score = raw_score
	return raw_score, scaled_score


def calculate_weighted_score(
	item_id,
	scaled_scores,
	weights,
):
	w1, w2, w3, w4, w5 = weights

	coherence = scaled_scores['coherence'].get(item_id, 0.0)
	importance = scaled_scores['importance'].get(item_id, 0.0)
	preference = scaled_scores['preference'].get(item_id, 0.0)
	nonmonotonousness = scaled_scores['nonmonotonousness'].get(item_id, 0.0)
	freshness = scaled_scores['freshness'].get(item_id, 0.0)

	return (
		w1 * coherence + w2 * importance + w3 * preference + w4 * nonmonotonousness + w5 * freshness
	)


##################################################
#### DECISION MAKING FUNCTIONS ######
##################################################
def choose_item(
	self,
	memory_bank: list[Item],
	score_sources: dict[str, dict[UUID, tuple[float, float]]],
	weights: tuple[float, float, float, float, float],
):
	scaled_scores = {
		'coherence': {},
		'importance': {},
		'preference': {},
		'nonmonotonousness': {},
		'freshness': {},
	}
	# print score sources for debugging
	# print("Score Sources: ", score_sources)

	total_raw_scores = {}

	for item in memory_bank:
		item_id = item.id
		raw_score_sum = 0
		for key in score_sources:
			# STATEMENT TO HAVE RAW SCORE = SHARED SCORE
			if key != 'preference':
				raw_score_sum += score_sources[key][item_id][0]
				scaled_scores[key][item_id] = score_sources[key][item_id][1]

		# print(f"Item ID: {item_id} | Raw Score Sum: {raw_score_sum}")
		total_raw_scores[item_id] = raw_score_sum

	total_weighted_scores = {
		item.id: calculate_weighted_score(item.id, scaled_scores, weights) for item in memory_bank
	}

	# Combine weighted and raw scores for final decision
	a = 0.5
	b = 1 - a
	# THIS IS A TEST

	final_scores = {
		item.id: a * total_weighted_scores[item.id] + b * total_raw_scores[item.id]
		for item in memory_bank
	}

	# If no final scores, return None
	# print all final scores for debugging by uuid
	# for item_id, score in final_scores.items():
	# print(f"Item ID: {item_id} | Final Score: {score}")

	if not final_scores:
		return None
	# If the best score is less than .15, we should pause (THIS IS FOR SHARED SCORES)
	elif max(final_scores.values()) < self.threshold:
		# print(f"*** We Didn't meet threshold: ", final_scores.values())
		return None, 0.0, final_scores

	# Best candidate now
	best_item_id, best_now = max(final_scores.items(), key=lambda kv: kv[1])
	best_item = next((it for it in memory_bank if it.id == best_item_id), None)

	# Return Best Item and its score, weighted scores for pause decision
	return best_item, best_now, final_scores

	# Takes in the total memory bank and scores each item based on whatever weighting system we have
	# Actually should make this a function in the class so it can have access to the contributed items/memory bank
	# Should automatically score things that were already in the contributed items a 0

	# As its scored, add it to a set thats sorted by the score. Return Set


##################################################
# Helper functions for pause decisions
##################################################


def average_score_last_n(memory_bank, history: list[Item], n: int, player) -> float:
	# Calculate the average score of the last n items in history (ignoring None)

	if len(history) >= n:
		importance_scores = [item.importance for item in history[-n:] if item is not None]
		coherence_scores = [
			score_coherence(player, item, history, memory_bank)[1]
			for item in history[-n:]
			if item is not None
		]
		scores = [
			(importance + coherence)
			for importance, coherence in zip(importance_scores, coherence_scores, strict=False)
		]
		if not scores:
			return 0.0
		return sum(scores) / len(scores)
	# If the history is less than n but greater than 0, return a lower threshold (encorage speaking to start the game)
	elif len(history) == 0:
		return -0.5
	else:
		return 0.0


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
	turns_so_far = len(history)  # history length
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


#  see what categories of points the other players tend to win, in terms of raw score
# predict who'll speak next!
