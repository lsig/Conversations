from models.player import Item, Player, PlayerSnapshot


class Player8(Player):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:  # noqa: F821
		super().__init__(snapshot, conversation_length)

	@staticmethod
	def was_last_round_pause(history: list[Item]) -> bool:
		return len(history) >= 1 and history[-1] is None

	@staticmethod
	def get_last_n_subjects(history: list[Item], n: int) -> set[str]:
		return set(
			subject for item in history[-n:] if item is not None for subject in item.subjects
		)

	def get_fresh_items(self, history: list[Item]) -> list[Item]:
		fresh_items = []
		prev_subjects = self.get_last_n_subjects(history, 5)
		for item in self.memory_bank:
			for subject in item.subjects:
				fresh_subject = subject not in prev_subjects
				used_by_self = item in self.contributed_items
				used_by_someone_else = item in history and not used_by_self
				if (
					fresh_subject
					and not used_by_someone_else
					and not used_by_self
					and item not in fresh_items
				):
					fresh_items.append(item)
		return fresh_items

	def get_most_important_item(self, items: list[Item]) -> Item | None:
		if not items:
			return None
		return max(items, key=lambda item: item.importance)

	def get_on_subject_items(self, history: list[Item]) -> list[Item]:
		context_subjects = self.get_last_n_subjects(history, 3)
		on_subject_items = []

		for item in self.memory_bank:
			for subject in item.subjects:
				used_by_self = item not in self.contributed_items
				used_by_someone_else = item in history and item not in self.contributed_items
				item_has_current_subject = subject in context_subjects

				if (
					not used_by_someone_else
					and not used_by_self
					and item_has_current_subject
					and item not in on_subject_items
				):
					on_subject_items.append(item)
		return on_subject_items

	"""
	Propose an item based on the conversation history.
		If the last round was a pause, propose a fresh item unrelated to recent subjects. -> Maximize Freshness, Importance while minimizing Repetition.
		Otherwise, propose the most important item related to the last 3  subjects. - > Maximize Coherence, Importance while minimizing Repetition.

		Scope to improve:
			- know when to pause.
			- handle edge cases better (e.g., no fresh items available).
	"""

	def propose_item(self, history: list[Item]) -> Item | None:
		if self.was_last_round_pause(history):
			fresh_items = self.get_fresh_items(history)
			most_important_fresh_item = self.get_most_important_item(fresh_items)
			return most_important_fresh_item

		on_subject_items = self.get_on_subject_items(history)
		most_important_on_subject_item = max(
			on_subject_items, key=lambda item: item.importance, default=None
		)

		return most_important_on_subject_item
