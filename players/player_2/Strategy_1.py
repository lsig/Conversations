from models.item import Item
from models.player import Player
from players.player_2.BaseStrategy import BaseStrategy


class Strategy1(BaseStrategy):
	def __init__(self):
		super().__init__()

	def propose_item(self, player: Player, history: list[Item]) -> Item | None:
		turn_nr = len(history) + 1

		# If last proposed item was accepted, remove it from memory bank and sub_to_item
		if turn_nr > 1 and history[-1] == player.last_proposed_item:
			last_proposed_subjects = tuple(sorted(list(player.last_proposed_item.subjects)))
			player.memory_bank.remove(player.last_proposed_item)
			player.sub_to_item[last_proposed_subjects].remove(player.last_proposed_item)

			# If we still have items with those subjects, propose the most valuable one
			if (
				last_proposed_subjects in player.sub_to_item
				and len(player.sub_to_item[last_proposed_subjects]) != 0
			):
				# print(f"Still have items with subjects {player.sub_to_item[last_proposed_subjects]}")
				most_valuable_item = max(
					player.sub_to_item[last_proposed_subjects],
					key=lambda item: self._get_imp_pref_score(item, player),
				)
				# print(f"Most valuable item: {most_valuable_item}")
				player.last_proposed_item = most_valuable_item
				return most_valuable_item

		# For the first turn, propose an item I can further be coherent with
		# Do the same if in the previous turn there was a pause
		if turn_nr == 1 or turn_nr > 1 and history[-1] is None:
			# Get the items with the most frequent occurring subject in memory bank

			_, coherent_items = next(iter(player.sub_to_item.items()))

			# Pick the most valuable item
			most_valuable_item = max(
				coherent_items, key=lambda item: self._get_imp_pref_score(item, player)
			)
			player.last_proposed_item = most_valuable_item

			return most_valuable_item

		# After the first turn, check history to decide proposal
		if turn_nr > 1:
			context = history[-3:]
			# Context doesn't extend over pause
			if None in context:
				context = context[context.index(None) + 1 :]

			context_subs_sorted = self._get_subjects_counts_sorted(context, player)

			# Go through all subjects in context, sorted according to frequency in context and then by number of items in own memory bank
			# If there are no items in memory bank that match the subjects in context, then pause

			for subs, subs_count in context_subs_sorted:
				if subs_count < 3:
					items_with_subs = player.sub_to_item.get(subs, []).copy()
					# If there is only one subject, also get items with two subjects including that subject
					if len(subs) == 1:
						items_with_subs.extend(
							[
								item
								for items_subs, items in player.sub_to_item.items()
								if subs[0] in items_subs
								for item in items
							]
						)

					# If we have an item with fitting subjects, propose the most valuable one
					if items_with_subs:
						most_valuable_item = max(
							items_with_subs, key=lambda item: self._get_imp_pref_score(item, player)
						)
						player.last_proposed_item = most_valuable_item

						return most_valuable_item

		return None
