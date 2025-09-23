from collections import Counter

from models.player import GameContext, Item, Player, PlayerSnapshot
from players.player_2.BaseStrategy import BaseStrategy
from players.player_2.ObservantStrategy import ObservantStrategy


class Player2(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)
		self.snapshot = snapshot
		self.subject_num: int = len(self.preferences)
		self.memory_bank_size: int = len(self.memory_bank)
		self.number_of_players: int = ctx.number_of_players
		self.conversation_length: int = ctx.conversation_length

		self.player_id: int = snapshot.id
		self.current_strategy: BaseStrategy = None
		self.scores_per_player = {}

		self.turn_nr: int = 0
		self.min_threshold: float = 1.0

		self.sub_to_item: dict = self._init_sub_to_item()
		self.last_proposed_item: Item = None

		self._compute_strategy_features()
		self._choose_strategy()

	def propose_item(self, history: list[Item]) -> Item | None:
		self.turn_nr += 1
		self._get_group_scores_per_turn(history)

		return self.current_strategy.propose_item(self, history)

	def _choose_strategy(self):
		self.current_strategy = ObservantStrategy(self, min_threshold=1.5)
	
	def _init_sub_to_item(self):
		sub_to_item = {}
		for item in self.memory_bank:
			subjects = tuple(sorted(list(item.subjects)))
			if subjects not in sub_to_item:
				sub_to_item[subjects] = []
			sub_to_item[subjects].append(item)

		# Sorted according to number of items in memory bank
		return dict(sorted(sub_to_item.items(), key=lambda x: len(x[1]), reverse=True))
		
	# Taken and adapted from engine.py
	def _calculate_freshness_score(self, i: int, current_item: Item, history) -> float:
		if i == 0 or history[i - 2] is not None:
			return 0.0

		prior_items = (item for item in history[max(-1, i - 7) : i - 2] if item is not None)
		prior_subjects = {s for item in prior_items for s in item.subjects}

		novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]

		return float(len(novel_subjects))

	# Taken and adapted from engine.py
	def _calculate_coherence_score(self, i: int, current_item: Item, history) -> float:
		context_items = []

		for j in range(i - 2, max(-2, i - 5), -1):
			if history[j] is None:
				break
			context_items.append(history[j])

		context_subject_counts = Counter(s for item in context_items for s in item.subjects)
		score = 0.0

		if not all(subject in context_subject_counts for subject in current_item.subjects):
			score -= 1.0

		if all(context_subject_counts.get(s, 0) >= 2 for s in current_item.subjects):
			score += 1.0

		return score

	# Taken and adapted from engine.py
	def _calculate_nonmonotonousness_score(self, i: int, current_item: Item, history) -> float:
		for item in history[: i - 1]:
			if item and item.id == current_item.id:
				return -1.0

		if i < 3:
			return 0.0

		last_three_items = [history[j] for j in range(i - 4, i - 1)]
		if all(
			item and any(s in item.subjects for s in current_item.subjects)
			for item in last_three_items
		):
			return -1.0

		return 0.0

	def _get_group_scores_per_turn(self, history):
		if len(history) == 0 or history[-1] is None:
			return None

		item = history[-1]
		pid = item.player_id

		importance = item.importance
		coherence = self._calculate_coherence_score(self.turn_nr - 1, item, history)
		freshness = self._calculate_freshness_score(self.turn_nr - 1, item, history)
		nonmono = self._calculate_nonmonotonousness_score(self.turn_nr - 1, item, history)
		importance = item.importance if nonmono != -1.0 else 0.0

		group_score = importance + coherence + freshness + nonmono
		if pid not in self.scores_per_player:
			self.scores_per_player[pid] = []
		self.scores_per_player[pid].append(group_score)
		return None

	def _get_negative_score_players(self):
		negative_players = []
		for pid, scores in self.scores_per_player.items():
			if scores and (sum(scores) / len(scores)) < 0:
				negative_players.append(pid)
		return negative_players
	
	def _compute_strategy_features(self):
		"""Compute minimal signals as attributes for picking Observant vs Inobservant."""
		P = self.number_of_players
		B = self.memory_bank_size
		L = max(1, self.conversation_length)
		S = max(1, self.subject_num)

		# Core knob: how crowded the game is with items per turn
		self.density: float = (P * B) / L

		# Inventory structure & importance stats
		n_single = 0
		n_pair = 0
		imp_sum = 0.0
		imp_max = 0.0
		counts_per_subject: Counter[int] = Counter()

		for it in self.memory_bank:
			k = len(it.subjects)
			if k == 1:
				n_single += 1
			elif k == 2:
				n_pair += 1

			imp_sum += it.importance
			if it.importance > imp_max:
				imp_max = it.importance

			for s in it.subjects:
				counts_per_subject[s] += 1

		self.n_single: int = n_single
		self.n_pair: int = n_pair
		self.two_subject_ratio: float = (n_pair / B) if B else 0.0
		self.avg_importance: float = (imp_sum / B) if B else 0.0
		self.max_importance: float = imp_max

		# Freshness & coherence capacity
		self.counts_per_subject: Counter[int] = counts_per_subject
		self.coverage_ratio: float = (
			(len(counts_per_subject) / S) if S else 0.0
		)  # breadth across subjects
		self.self_coherence_capacity: int = sum(1 for c in counts_per_subject.values() if c >= 2)

		# Two-subject bridges that are supported by extra items on at least one side
		bridge_ready_pairs = 0
		for key, items in self.sub_to_item.items():
			if len(key) == 2:
				a, b = key
				if counts_per_subject[a] >= 2 or counts_per_subject[b] >= 2:
					bridge_ready_pairs += len(items)
		self.bridge_ready_pairs: int = bridge_ready_pairs
