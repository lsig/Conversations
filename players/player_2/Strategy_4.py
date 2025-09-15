from models.item import Item
from models.player import Player
from players.player_2.BaseStrategy import BaseStrategy


class Strategy4(BaseStrategy):
	def propose_item(self, player: Player, history: list[Item]) -> Item | None:
		# last entry was a pause
		after_pause = bool(history) and history[-1] is None

		# recent non-pause context
		non_pause = [it for it in history if it is not None]
		last3 = list(reversed(non_pause))[:3]
		last5 = list(reversed(non_pause))[:5]
		last5_subjects = {s for it in last5 for s in it.subjects}

		# engines monotony check uses the last 3 entries - including pauses
		last3_entries = history[-3:] if len(history) >= 3 else history[:]
		last3_entries_all_items = len(last3_entries) == 3 and all(
			e is not None for e in last3_entries
		)

		# preferences - lower index = higher preference
		prefs = {s: idx for idx, s in enumerate(player.preferences)}
		S = len(player.preferences) if player.preferences else 1

		def pref_bonus(item: Item) -> float:
			# avg(1 - rank/|S|) over the items subjects
			return sum(1.0 - (prefs.get(s, S - 1) / S) for s in item.subjects) / len(item.subjects)

		def recent_overlap(item: Item) -> int:
			# how many of item’s subjects showed up in the last 3 non-pause items
			recent_subs = {s for it in last3 for s in it.subjects}
			return len(set(item.subjects) & recent_subs)

		def novel_after_pause(item: Item) -> int:
			# right after a pause: count subjects not seen in last5 (0/1/2)
			if not after_pause:
				return 0
			return sum(1 for s in set(item.subjects) if s not in last5_subjects)

		def triggers_monotony(item: Item) -> bool:
			# only if last 3 entries are items and each overlaps this item
			if not last3_entries_all_items:
				return False
			curr = set(item.subjects)
			last_three = [e for e in last3_entries if e is not None]
			return all(any(s in it.subjects for s in curr) for it in last_three)

		# no repeats
		used_ids = {it.id for it in non_pause}
		candidates = [it for it in player.memory_bank if it.id not in used_ids]
		if not candidates:
			return None

		safe = [it for it in candidates if not triggers_monotony(it)]
		if not safe:
			return None

		# greedy keys
		def rank_after_pause(item: Item):
			# more novel / higher importance / higher preference; slight nudge for “bridge” pairs
			nov = novel_after_pause(item)  # 0/1/2
			imp = item.importance
			pb = pref_bonus(item)
			bridge = False
			if len(item.subjects) == 2:
				s1, s2 = item.subjects
				bridge = (s1 in last5_subjects) ^ (s2 in last5_subjects)  # exactly one fresh
			return (nov, bridge, imp, pb)

		def rank_normal(item: Item):
			# more recent overlap / higher importance / higher preference
			ov = recent_overlap(item)  # 0/1/2
			imp = item.importance
			pb = pref_bonus(item)
			return (ov, imp, pb)

		if after_pause:
			safe.sort(key=rank_after_pause, reverse=True)
		else:
			safe.sort(key=rank_normal, reverse=True)

		return safe[0] if safe else None
