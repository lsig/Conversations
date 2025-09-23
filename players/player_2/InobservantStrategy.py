from models.item import Item
from models.player import Player
from players.player_2.BaseStrategy import BaseStrategy


class InobservantStrategy(BaseStrategy):
	def __init__(self, player: Player) -> None:
		super().__init__(player)
		self.min_imp_pref_score = 0
		self.trimester = 1

	def propose_item(self, player: Player, history: list[Item]) -> Item | None:
		turn_nr = len(history) + 1
		num_p = self.player.number_of_players

		# Don't propose if no items left
		if len(player.sub_to_item) == 0:
			return None

		# update the current trimester
		if turn_nr > self.trimester * (player.conversation_length + 2) // 3:
			self.trimester += 1

		# Remove if proposal was accepted last turn
		if turn_nr > 1 and history[-1] is not None and history[-1] == player.last_proposed_item:
			last_proposed_subjects = tuple(sorted(list(player.last_proposed_item.subjects)))
			self._remove_item_from_dict(player, last_proposed_subjects)

			# If we still have items with those subjects, propose the most valuable one
			if (
				last_proposed_subjects in player.sub_to_item
				and len(player.sub_to_item[last_proposed_subjects]) != 0
			):
				most_valuable_item = max(
					player.sub_to_item[last_proposed_subjects],
					key=lambda item: self._get_imp_pref_score(item, player),
				)
				# print(f"Most valuable item: {most_valuable_item}")
				player.last_proposed_item = most_valuable_item
				return most_valuable_item

		# Observe for obs_num turns
		if turn_nr <= self.obs_num:
			# If last turn the second pause occurred then try to be coherent no matter what
			if len(history) > 0 and history[-1] is None and history.count(None) == 2:
				return self._propose_coherently(player, history)
			if num_p > 2 and (turn_nr == 1 or (turn_nr > 1 and history[-1] is not None)):
				# in observation period and other people are talking - so don't propose anything
				return None

		# go for freshness after a pause if possible - always - even if in a bad trimester
		if turn_nr > 1 and history[-1] is None:
			proposed_item = self._propose_freshly(player, history)
			return proposed_item

		# space out usage by saving items for later trimesters, unless 2 pauses occur - then go for it
		unused_size = len(player.sub_to_item)
		if unused_size < player.memory_bank_size * (3 - self.trimester) // 3:
			return None

		else:
			# go for coherence when possible to do so
			proposed_item = self._propose_coherently(player, history)
			return proposed_item

	def _remove_item_from_dict(self, player: Player, subjects: tuple[int, ...]) -> None:
		player.sub_to_item[subjects].remove(player.last_proposed_item)
		if len(player.sub_to_item[subjects]) == 0:
			del player.sub_to_item[subjects]

	def _get_context(self, history: list[Item]) -> list[Item]:
		context = history[-3:]
		# Context doesn't extend over pause
		if None in context:
			context = context[context.index(None) + 1 :]
		return context

	# propose freshly - if there is a pause - immediately attempt to take convo back if possible
	# finds item to maximize freshness
	# make a copy and sort? Probably a better idea
	def _propose_freshly(self, player, history) -> Item | None:
		# collect all subjects in previous 5 turns in prev_subs
		prev_subs = []
		filtered_dict = player.sub_to_item.copy()
		for sub in history[-5:]:
			if sub is not None:
				prev_subs.append(sub)

		# filter out all items with subjects that were previously mentioned in past 5 turns
		for sub in prev_subs:
			filtered_dict = dict(filter(lambda x: sub not in x[0], filtered_dict.items()))

		if len(filtered_dict) != 0:
			# maximize freshness - grab items with 2 subjects if possible, else grab items with
			sub_length = 0
			sub_key = tuple()
			for key in filtered_dict:
				if len(filtered_dict[key]) > sub_length:
					sub_length = len(filtered_dict[key])
					sub_key = key
			most_valuable_item = max(
				filtered_dict[sub_key], key=lambda item: self._get_imp_pref_score(item, player)
			)
			player.last_proposed_item = most_valuable_item
			return most_valuable_item

		# otherwise propose an option that will allow a story to be told
		else:
			return self._propose_possible_coherence(player)

	# always propose item that hopefully can maximize future coherence + with the most importance + preference score
	def _propose_possible_coherence(self, player) -> Item | None:
		_, next_items = next(iter(player.sub_to_item.items()))

		# Pick the most valuable item
		most_valuable_item = max(
			next_items, key=lambda item: self._get_imp_pref_score(item, player)
		)
		player.last_proposed_item = most_valuable_item
		return most_valuable_item

	# proposes an item that is coherent
	def _propose_coherently(self, player, history) -> Item | None:
		context = self._get_context(history)

		context_subs_sorted = self._get_subjects_counts_sorted(context, player)
		# Go through all subjects in context, sorted according to frequency in context and then by number of items in own memory bank
		# If there are no items in memory bank that match the subjects in context, then pause
		for subs, subs_count in context_subs_sorted:
			# If a subject already occurred thrice then we don't want to be monotonous
			# if subject was repeated 3 times even if contained in 2 subject item
			if subs_count < 3:
				items_with_subs = player.sub_to_item.get(subs, []).copy()
				# If there is only one subject, also get items with two subjects including that subject
				if len(subs) == 1:
					# print(f"Also look for items with subject {subs} and another subject")
					items_with_subs.extend(
						[
							item
							for items_subs, items in player.sub_to_item.items()
							if subs[0] in items_subs
							for item in items
						]
					)

				# If the subject only occurred once in the context and we only have one item with this subject, propose it if it meets the threshold, or we said the last item
				if (
					subs_count == 1
					and len(items_with_subs) == 1
					and (
						items_with_subs[0].importance > self.min_imp_pref_score
						or (history[-1] is not None and history[-1].player_id == player.id)
					)
				):
					player.last_proposed_item = items_with_subs[0]
					return items_with_subs[0]

				# If we have an item with fitting subjects, propose the most valuable one
				if items_with_subs:
					most_valuable_item = max(
						items_with_subs, key=lambda item: self._get_imp_pref_score(item, player)
					)
					player.last_proposed_item = most_valuable_item
					return most_valuable_item

		return None
