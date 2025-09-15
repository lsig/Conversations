from __future__ import annotations

from models.item import Item
from models.player import Player, PlayerSnapshot
from players.player_2.BaseStrategy import BaseStrategy


class Strategy3(BaseStrategy):
	def propose_item(self, player: Player, history: list[Item | None]) -> Item | None:
		if not player.memory_bank:
			return None

		# Collect ids already used to filter repeats early (repeats are always dominated).
		used_ids = {it.id for it in history if isinstance(it, Item)}

		# Snapshot-like container (for individual scoring parity).
		snapshot_like = PlayerSnapshot(
			id=player.id,
			preferences=tuple(player.preferences),
			memory_bank=tuple(player.memory_bank),
		)

		def individual_bonus(item: Item) -> float:
			prefs = snapshot_like.preferences
			bonuses = [1 - prefs.index(s) / len(prefs) for s in item.subjects if s in prefs]
			return sum(bonuses) / len(bonuses) if bonuses else 0.0

		def coherence_score(temp_history: list[Item | None], idx: int, item: Item) -> float:
			# Collect backward context until pause or up to 3 items
			context_items: list[Item] = []
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
			# penalty if any subject absent
			if not all(s in context_subject_counts for s in item.subjects):
				score -= 1.0
			# bonus if all subjects seen at least twice
			if all(context_subject_counts.get(s, 0) >= 2 for s in item.subjects):
				score += 1.0
			return score

		def freshness_score(temp_history: list[Item | None], idx: int, item: Item) -> float:
			# Freshness only if immediately after a pause.
			if idx == 0:
				return 0.0
			if temp_history[idx - 1] is not None:
				return 0.0
			# Look back up to 5 concrete items before the pause.
			k = idx - 2
			concrete_back: list[Item] = []
			while k >= 0 and len(concrete_back) < 5:
				h_it = temp_history[k]
				if h_it is None:
					break  # stop at earlier pause
				concrete_back.append(h_it)
				k -= 1
			prior_subjects = {s for it in concrete_back for s in it.subjects}
			novel = [s for s in item.subjects if s not in prior_subjects]
			return float(len(novel))

		def nonmonotonousness_score(temp_history: list[Item | None], idx: int, item: Item) -> float:
			# Repeated item penalty.
			if any(h and h.id == item.id for h in temp_history[:idx]):
				return -1.0
			# If fewer than 3 prior concrete items no monotony penalty.
			concrete_back = [h for h in temp_history[:idx] if isinstance(h, Item)]
			if len(concrete_back) < 3:
				return 0.0
			last_three = concrete_back[-3:]
			if all(any(s in prev.subjects for s in item.subjects) for prev in last_three):
				return -1.0
			return 0.0

		best_item: Item | None = None
		best_score = float('-inf')

		base_len = len(history)

		for candidate in player.memory_bank:
			# Skip repeats (Engine would allow but yields dominated score: importance=0 + penalty). Could include if exploring bluffing.
			if candidate.id in used_ids:
				continue

			# Hypothetical history with candidate appended.
			temp_history = history + [candidate]
			idx = base_len  # index where candidate would sit

			importance = candidate.importance
			coherence = coherence_score(temp_history, idx, candidate)
			freshness = freshness_score(temp_history, idx, candidate)
			nonmono = nonmonotonousness_score(temp_history, idx, candidate)
			indiv = individual_bonus(candidate)

			# If repeated (not possible here due to skip) importance & others would be zero/penalty.
			shared_total = importance + coherence + freshness + nonmono
			total = shared_total  # + indiv # Currently not using individual bonus to avoid overfitting to self

			if total > best_score:
				best_score = total
				best_item = candidate
			elif total == best_score and best_item is not None:
				# Deterministic tie-break: higher importance, then fewer subjects, lexicographic.
				if importance > best_item.importance or (
					importance == best_item.importance
					and (len(candidate.subjects), candidate.subjects)
					< (len(best_item.subjects), best_item.subjects)
				):
					best_item = candidate

		return best_item
