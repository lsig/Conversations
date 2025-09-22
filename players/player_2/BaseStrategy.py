from abc import ABC, abstractmethod
from collections import Counter

from models.item import Item
from models.player import Player


class BaseStrategy(ABC):
	def __init__(self, player: Player) -> None:
		super().__init__()
		self.player: Player = player
		self.obs_num: int = self._init_obs_num()
		self.min_imp_pref_score: float = 0

	def _init_obs_num(self):
		num_p = self.player.number_of_players
		c_len = self.player.conversation_length
		obs_num = num_p
		if num_p - 1 > c_len // 3:
			obs_num = c_len // 3
		return obs_num

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
				(tuple(sorted(list(subs))) if isinstance(subs, tuple) else (subs,), count)
				for subs, count in subs_count.items()
			),
			key=lambda x: (
				-x[1],
				-self._count_items_with_subject(x[0], player),
			),
		)

		return subs_sorted_by_count

	def _count_items_with_subject(self, subjects: tuple[int, ...], player: Player) -> int:
		count = len(player.sub_to_item[subjects]) if subjects in player.sub_to_item else 0
		if len(subjects) == 1:
			for subs, items in player.sub_to_item.items():
				if len(subs) == 2 and subjects[0] in subs:
					count += len(items)
		return count

	def _get_pref_score(self, item: Item, player: Player) -> float:
		item_bonuses = [
			1 - (player.preferences.index(sub)) / player.subject_num for sub in item.subjects
		]
		final_bonus = sum(item_bonuses) / len(item_bonuses)
		return final_bonus

	def _get_imp_pref_score(self, item: Item, player: Player) -> float:
		"""Calculate overall score of an item based on its importance and individual bonuses."""

		item_bonuses = [
			1 - (player.preferences.index(sub)) / player.subject_num for sub in item.subjects
		]
		final_bonus = sum(item_bonuses) / len(item_bonuses)

		overall_score = item.importance + final_bonus
		return overall_score

	@abstractmethod
	def propose_item(self, player: Player, history: list[Item]) -> Item | None:
		pass
