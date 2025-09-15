from collections import Counter

from models.item import Item
from models.player import Player
from players.player_2.BaseStrategy import BaseStrategy


class Strategy1(BaseStrategy):
	def __init__(self):
		super().__init__()

	def propose_item(self, player: Player, history: list[Item]) -> Item | None:
		turn_nr = len(history) + 1
		# print(f"Turn nr {turn_nr} / {player.conversation_length}")

		# TODO: Add a subject to bonus dict to Player2 init??
		# sub_to_bonus = {sub: 1 - (player.preferences.index(sub)) / player.subject_num for sub in range(player.subject_num)}
		# print(sub_to_bonus)

		# Sort memory bank dictionary by number of items
		# TODO: already do this in init
		player.sub_to_item = dict(
			sorted(player.sub_to_item.items(), key=lambda x: len(x[1]), reverse=True)
		)

		# If last proposed item was accepted, remove it from memory bank and sub_to_item
		if turn_nr > 1 and history[-1] == player.last_proposed_item:
			# print(f"Remove last proposed item: {player.last_proposed_item}")

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
					key=lambda item: self._get_overall_score(item, player),
				)
				# print(f"Most valuable item: {most_valuable_item}")
				player.last_proposed_item = most_valuable_item
				return most_valuable_item

		# Comment this out before merge!!!
		# for subs, items in player.sub_to_item.items():
		# 	print(f"Subjects: {subs}, Importances: {[item.importance for item in items]}")

		# For the first turn, propose an item I can further be coherent with
		# Do the same if in the previous turn there was a pause
		if turn_nr == 1 or turn_nr > 1 and history[-1] is None:
			# print("Here in first turn or after pause")
			# Get the items with the most frequent occurring subject in memory bank
			_, coherent_items = next(iter(player.sub_to_item.items()))
			# print(f"Coherent items: {coherent_items}")

			# Pick the most valuable item
			most_valuable_item = max(
				coherent_items, key=lambda item: self._get_overall_score(item, player)
			)
			player.last_proposed_item = most_valuable_item

			# print(f"Most valuable item: {most_valuable_item}")
			return most_valuable_item

		# After the first turn, check history to decide proposal
		if turn_nr > 1:
			# print("Here after first turn")
			context = history[-3:]
			# Context doesn't extend over pause
			if None in context:
				context = context[context.index(None) + 1 :]

			context_subs_sorted = self._get_subjects_counts_sorted(context, player)
			# print(f"Sorted: {context_subs_sorted}")

			# Go through all subjects in context, sorted according to frequency in context and then by number of items in own memory bank
			# If there are no items in memory bank that match the subjects in context, then pause
			for subs, _ in context_subs_sorted:
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

				# print(f"Items with subjects {subs}: {items_with_subs}")
				# If we have an item with fitting subjects, propose the most valuable one
				if items_with_subs:
					most_valuable_item = max(
						items_with_subs, key=lambda item: self._get_overall_score(item, player)
					)
					player.last_proposed_item = most_valuable_item

					# print(f"Most valuable item: {most_valuable_item}")
					return most_valuable_item

		return None

	def _get_subjects_counts_sorted(self, items: list[Item], player: Player) -> list:
		"""Count occurrences of subjects in items and return them, first sorted by count, second sorted by occurence in player's memory bank."""

		subs_count = Counter()
		for item in items:
			if item is not None:
				subs_count.update(item.subjects)
				if len(item.subjects) == 2:
					subs_count[item.subjects] += 1

		subs_sorted_by_count = sorted(
			(
				(subs if isinstance(subs, tuple) else (subs,), count)
				for subs, count in subs_count.items()
			),
			key=lambda x: (
				-x[1],
				-len(player.sub_to_item[x[0]]) if x[0] in player.sub_to_item else 0,
			),
		)

		return subs_sorted_by_count

	def _get_overall_score(self, item: Item, player: Player) -> float:
		"""Calculate overall score of an item based on its importance and individual bonuses."""

		item_bonuses = [
			1 - (player.preferences.index(sub)) / player.subject_num for sub in item.subjects
		]
		final_bonus = sum(item_bonuses) / len(item_bonuses)

		overall_score = item.importance + final_bonus
		return overall_score
