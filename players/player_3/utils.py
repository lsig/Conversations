from collections import Counter

# from models.player import Item
from models.item import Item

DEFAULT_DISCOUNT_RATE = 0.9
DEFAULT_CONTEXT_LENGTH = 10


class ConversationScorer:
	"""Handles all score calculations for conversation items."""

	def __init__(self, player_preferences: list[int], competition_rate=0.5):
		self.competition_rate = competition_rate
		self.player_preferences = player_preferences

	def set_competition_rate(self, rate: float) -> None:
		self.competition_rate = rate

	def is_repeated(self, item: Item, history: list[Item]) -> bool:
		"""Check if item was already used in conversation."""
		return any(existing_item and existing_item.id == item.id for existing_item in history)

	def calculate_freshness_score(self, item: Item, position: int, history: list[Item]) -> float:
		"""Calculate freshness score (based on Engine's logic)."""
		if position == 0 or history[position - 1] is not None:
			return 0.0

		prior_items = (
			item for item in history[max(0, position - 6) : position - 1] if item is not None
		)
		prior_subjects = {s for item in prior_items for s in item.subjects}

		novel_subjects = [s for s in item.subjects if s not in prior_subjects]
		return float(len(novel_subjects))

	# def calculate_self_coherence_score(...)
	def calculate_coherence_score(self, item: Item, position: int, history: list[Item]) -> float:
		"""Calculate coherence score (based on Engine's logic)."""
		context_items = []

		# past
		for j in range(position - 1, max(-1, position - 4), -1):
			if history[j] is None:
				break
			context_items.append(history[j])

		# ORIGINAL (future context was included in BST scorer, but engine uses past-only):
		# for j in range(position + 1, min(len(history), position + 4)):
		# 	if history[j] is None:
		# 		break
		# 	context_items.append(history[j])

		context_subject_counts = Counter(s for item in context_items for s in item.subjects)
		score = 0.0

		if not all(subject in context_subject_counts for subject in item.subjects):
			score -= 1.0

		if all(context_subject_counts.get(s, 0) >= 2 for s in item.subjects):
			score += 1.0

		return score

	def calculate_nonmonotonousness_score(
		self, item: Item, position: int, history: list[Item], repeated: bool
	) -> float:
		"""Calculate nonmonotonousness score (based on Engine's logic)."""
		if repeated:
			return -1.0

		if position < 3:
			return 0.0

		last_three_items = [history[j] for j in range(position - 3, position)]
		# any(s in item.subjects for s in item.subjects)
		# Fix: compare current item's subjects against subjects of each of the last three items
		if all(
			last_item and any(s in last_item.subjects for s in item.subjects)
			for last_item in last_three_items
		):
			return -1.0

		return 0.0

	# past coherence update because of the new item.
	def calculate_others_coherence_score_update(
		self, item: Item, position: int, history: list[Item]
	) -> float:
		"""Calculate how adding this item affects coherence scores of past items."""
		# used calculate_self_coherence_score, appended wrong variable, and summed with fixed range(3)
		original_scores = []
		for i in range(max(0, position - 3), position):
			if history[i] is None:
				continue
			original_score = self.calculate_coherence_score(history[i], i, history)
			original_scores.append(original_score)

		new_scores = []
		history.append(item)
		for i in range(max(0, position - 3), position):
			if history[i] is None:
				continue
			new_score = self.calculate_coherence_score(history[i], i, history)
			new_scores.append(new_score)
		history.pop()

		# Sum differences safely over aligned pairs
		return sum(ns - os for ns, os in zip(new_scores, original_scores, strict=False))

	def calculate_individual_score(self, item: Item) -> float:
		"""Calculate individual score based on player preferences (based on Engine's logic)."""
		bonuses = [
			1 - self.player_preferences.index(s) / len(self.player_preferences)
			for s in item.subjects
			if s in self.player_preferences
		]
		if bonuses:
			return sum(bonuses) / len(bonuses)
		return 0.0

	def calculate_shared_score(self, item, history):
		"""Calculate total score impact for adding this item (replicating Engine logic)."""
		position = len(history)
		is_repeated = self.is_repeated(item, history)

		# Shared score components (align with Engine's _calculate_turn_score_impact)
		if is_repeated:
			importance = 0.0
			coherence = 0.0
			freshness = 0.0
		else:
			importance = item.importance
			# ORIGINAL (BST added retroactive update):
			coherence = self.calculate_coherence_score(
				item, position, history
			) + self.calculate_others_coherence_score_update(item, position, history)
			# coherence = self.calculate_coherence_score(item, position, history)
			freshness = self.calculate_freshness_score(item, position, history)

		nonmonotonousness = self.calculate_nonmonotonousness_score(
			item, position, history, is_repeated
		)

		# Total shared score (do not include retroactive coherence updates to match Engine)
		shared_total = importance + coherence + freshness + nonmonotonousness
		return shared_total

	def calculate_total_score(self, item: Item, history: list[Item]) -> float:
		# Individual score
		individual = self.calculate_individual_score(item)

		# Total shared score
		shared_total = self.calculate_shared_score(item, history)

		return shared_total + individual

	def evaluate(self, item, history: list[Item]):
		individual_score = self.calculate_individual_score(item)
		shared_score = self.calculate_shared_score(item, history)
		weighted_score = (
			self.competition_rate * individual_score + (1 - self.competition_rate) * shared_score
		)
		return weighted_score

	def calculate_expected_score(
		self,
		history: list[Item],
		mode: str = 'discount_average',
		context_length: int = DEFAULT_CONTEXT_LENGTH,
		discount_rate: float = DEFAULT_DISCOUNT_RATE,
	) -> float:
		"""
		Compute an expected score from recent history using this scorer.

		- mode == "average": simple average of recent, non-empty turns
		- mode == "discount_average": exponentially discounted average with rate discount_rate

		context_length controls how many most-recent turns to consider.
		"""
		if mode == 'average':
			discount_rate = 0

		if not history:
			return 0.0

		# Consider the last `context_length` turns
		start_index = max(0, len(history) - context_length)
		recent_indices = list(range(start_index, len(history)))

		# Build scores for non-None turns using the state as it was before that turn
		scored: list[tuple[int, float]] = []  # (rank_from_end, score)
		for j in recent_indices:
			item = history[j]
			if item is None:
				continue
			# history before item was proposed at turn j
			prior_history = history[:j]
			score = self.evaluate(item, prior_history)
			rank_from_end = (len(history) - 1) - j  # 0 for most recent
			scored.append((rank_from_end, score))

		if not scored:
			return 0.0

		# Discounted average (recent turns weigh more)
		sum_w = 0.0
		sum_ws = 0.0
		base = max(0.0, min(1.0, 1.0 - discount_rate))
		for rank, s in scored:
			w = base**rank
			sum_w += w
			sum_ws += w * s

		return sum_ws / sum_w if sum_w > 0 else 0.0
