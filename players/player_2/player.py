from models.player import GameContext, Item, Player, PlayerSnapshot
from players.player_2.BaseStrategy import BaseStrategy
from players.player_2.ObservantStrategy import ObservantStrategy


class Player2(Player):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:  # noqa: F821
		super().__init__(snapshot, ctx)
		self.snapshot = snapshot
		self.subject_num: int = len(self.preferences)
		self.memory_bank_size: int = len(self.memory_bank)
		self.current_strategy: BaseStrategy = None

		self.sub_to_item: dict = self._init_sub_to_item()
		self.last_proposed_item: Item = None
		self.scores_per_player: dict = {}
		self._choose_strategy()

	def propose_item(self, history: list[Item]) -> Item | None:
		self.get_group_scores_per_turn(history)
		negative_players = self.get_negative_score_players()
		return ObservantStrategy()

	def get_negative_score_players(self):
		# Returns a list of player_ids whose average group score per turn spoken is negative.
		negative_players = []
		for pid, scores in self.scores_per_player.items():
			if scores and (sum(scores) / len(scores)) < 0:
				negative_players.append(pid)
		return negative_players

	def get_group_scores_per_turn(self, history):
		# Updates self.scores_per_player with group scores for each turn spoken. Returns None.
		def coherence_score(temp_history, idx, item):
			context_items = []
			back_count = 0
			j = idx - 1
			while j >= 0 and back_count < 3:
				prev = temp_history[j]
				if prev is None:
					break
				context_items.append(prev)
				back_count += 1
				j -= 1
			context_subject_counts = {}
			for ctxt in context_items:
				for s in ctxt.subjects:
					context_subject_counts[s] = context_subject_counts.get(s, 0) + 1
			score = 0.0
			if not all(s in context_subject_counts for s in item.subjects):
				score -= 1.0
			if all(context_subject_counts.get(s, 0) >= 2 for s in item.subjects):
				score += 1.0
			return score

		def freshness_score(temp_history, idx, item):
			if idx == 0:
				return 0.0
			if temp_history[idx - 1] is not None:
				return 0.0
			k = idx - 2
			concrete_back = []
			while k >= 0 and len(concrete_back) < 5:
				h_it = temp_history[k]
				if h_it is None:
					break
				concrete_back.append(h_it)
				k -= 1
			prior_subjects = {s for it in concrete_back for s in it.subjects}
			novel = [s for s in item.subjects if s not in prior_subjects]
			return float(len(novel))

		def nonmonotonousness_score(temp_history, idx, item):
			if any(h and h.id == item.id for h in temp_history[:idx]):
				return -1.0
			concrete_back = [h for h in temp_history[:idx] if isinstance(h, Item)]
			if len(concrete_back) < 3:
				return 0.0
			last_three = concrete_back[-3:]
			if all(any(s in prev.subjects for s in item.subjects) for prev in last_three):
				return -1.0
			return 0.0

		for idx, item in enumerate(history):
			if item is None:
				continue
			pid = item.player_id # The player who proposed this item not sure if this is correct
			importance = item.importance
			coherence = coherence_score(history, idx, item)
			freshness = freshness_score(history, idx, item)
			nonmono = nonmonotonousness_score(history, idx, item)
			group_score = importance + coherence + freshness + nonmono
			if pid not in self.scores_per_player:
				self.scores_per_player[pid] = []
			self.scores_per_player[pid].append(group_score)
		return None


	def _init_sub_to_item(self):
		sub_to_item = {}
		for item in self.memory_bank:
			subjects = tuple(sorted(list(item.subjects)))
			if subjects not in sub_to_item:
				sub_to_item[subjects] = []
			sub_to_item[subjects].append(item)

		# Sorted according to number of items in memory bank
		return dict(sorted(sub_to_item.items(), key=lambda x: len(x[1]), reverse=True))
