import random
import uuid
from collections import Counter
from dataclasses import asdict

from models.item import Item
from models.player import GameContext, Player, PlayerSnapshot


class Engine:
	def __init__(
		self,
		players: list[type[Player]],
		player_count: int,
		subjects: int,
		memory_size: int,
		conversation_length: int,
		seed: int,
	) -> None:
		random.seed(seed)

		self.subjects = [i for i in range(subjects)]
		self.memory_size = memory_size
		self.conversation_length = conversation_length
		self.players_count = player_count

		self.history: list[Item | None] = []
		self.last_player_id: uuid.UUID | None = None
		self.turn = 0
		self.consecutive_pauses = 0
		self.player_contributions: dict[uuid.UUID, list[Item]] = {}
		self.snapshots = self.__initialize_snapshots(player_count)
		self.players = [
			player(
				snapshot=self.snapshots[id],
				ctx=GameContext(
					conversation_length=conversation_length, number_of_players=player_count
				),
			)
			for id, player in zip(list(self.snapshots.keys()), players, strict=True)
		]

		self.player_names = {player.id: player.name for player in self.players}

	def __initialize_snapshots(self, player_count) -> dict[uuid.UUID, PlayerSnapshot]:
		snapshots = {}

		for _ in range(player_count):
			id = uuid.uuid4()
			preferences = self.__generate_preference()
			memory_bank = self.__generate_items(player_id=id)

			snapshot = PlayerSnapshot(id=id, preferences=preferences, memory_bank=memory_bank)

			snapshots[id] = snapshot
			self.player_contributions[id] = []

		return snapshots

	def __generate_preference(self) -> tuple[int]:
		return tuple(random.sample(self.subjects, len(self.subjects)))

	def __generate_items(self, player_id: uuid.UUID) -> tuple[Item, ...]:
		items: list[Item] = []

		for _ in range(self.memory_size):
			samples = 1 if random.random() < 0.5 else 2

			importance = round(random.random(), 2)
			subjects = tuple(random.sample(self.subjects, samples))

			item = Item(
				id=uuid.uuid4(), player_id=player_id, importance=importance, subjects=subjects
			)
			items.append(item)

		return tuple(items)

	def __get_proposals(self) -> dict[uuid.UUID, Item | None]:
		proposals = {}
		for player in self.players:
			proposal = player.propose_item(self.history)

			if proposal and self.snapshots[player.id].item_in_memory_bank(proposal):
				proposals[player.id] = proposal

		return proposals

	def __select_speaker(
		self, proposals: dict[uuid.UUID, Item | None]
	) -> tuple[uuid.UUID | None, Item | None]:
		proposed_players = {uid: item for uid, item in proposals.items() if item}

		if not proposed_players:
			return None, None

		if (
			self.last_player_id
			and self.last_player_id in proposed_players
			and random.random() < 0.5
		):
			item = proposed_players[self.last_player_id]
			return self.last_player_id, item

		min_contributions = min(len(self.player_contributions[uid]) for uid in proposed_players)
		eligible_speakers = [
			uid
			for uid in proposed_players
			if len(self.player_contributions[uid]) == min_contributions
		]

		speaker_id = random.choice(eligible_speakers)
		item = proposed_players[speaker_id]

		return speaker_id, item

	def __calculate_freshness_score(self, i: int, current_item: Item) -> float:
		if i == 0 or self.history[i - 1] is not None:
			return 0.0

		prior_items = (item for item in self.history[max(0, i - 6) : i - 1] if item is not None)
		prior_subjects = {s for item in prior_items for s in item.subjects}

		novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]

		return float(len(novel_subjects))

	def __calculate_coherence_score(self, i: int, current_item: Item) -> float:
		context_items = []

		for j in range(i - 1, max(-1, i - 4), -1):
			if self.history[j] is None:
				break
			context_items.append(self.history[j])

		for j in range(i + 1, min(len(self.history), i + 4)):
			if self.history[j] is None:
				break
			context_items.append(self.history[j])

		context_subject_counts = Counter(s for item in context_items for s in item.subjects)
		score = 0.0

		if not all(subject in context_subject_counts for subject in current_item.subjects):
			score -= 1.0

		if all(context_subject_counts.get(s, 0) >= 2 for s in current_item.subjects):
			score += 1.0

		return score

	def __calculate_nonmonotonousness_score(
		self, i: int, current_item: Item, repeated: bool
	) -> float:
		if repeated:
			return -1.0

		if i < 3:
			return 0.0

		last_three_items = [self.history[j] for j in range(i - 3, i)]
		if all(
			item and any(s in item.subjects for s in current_item.subjects)
			for item in last_three_items
		):
			return -1.0

		return 0.0

	def __calculate_individual_score(self) -> dict[uuid.UUID, float]:
		individual_scores: dict[uuid.UUID, float] = {id: 0.0 for id in self.snapshots}

		for snapshot in self.snapshots.values():
			preferences = snapshot.preferences

			player_individual_score = 0.0
			for item in self.history:
				if not item:
					continue

				bonuses = [
					1 - preferences.index(s) / len(preferences)
					for s in item.subjects
					if s in preferences
				]
				if bonuses:
					player_individual_score += sum(bonuses) / len(bonuses)

			individual_scores[snapshot.id] = player_individual_score

		return individual_scores

	def __calculate_scores(self) -> dict[str, float]:
		total_shared_score = 0.0
		unique_items: set[uuid.UUID] = set()

		coherence_score = 0.0
		freshness_score = 0.0
		importance_score = 0.0
		nonmonotonousness = 0.0

		for i, current_item in enumerate(self.history):
			if not current_item:
				continue

			if current_item.id in unique_items:
				nonmonotonousness += self.__calculate_nonmonotonousness_score(
					i, current_item, repeated=True
				)
			else:
				importance_score += current_item.importance
				coherence_score += self.__calculate_coherence_score(i, current_item)
				freshness_score += self.__calculate_freshness_score(i, current_item)
				nonmonotonousness += self.__calculate_nonmonotonousness_score(
					i, current_item, repeated=False
				)

				unique_items.add(current_item.id)

		individual_scores = self.__calculate_individual_score()

		total_shared_score = (
			coherence_score + freshness_score + importance_score + nonmonotonousness
		)

		return {
			'shared': total_shared_score,
			'individual': individual_scores,
			'coherence': coherence_score,
			'freshness': freshness_score,
			'importance': importance_score,
			'nonmonotonousness': nonmonotonousness,
		}

	def final_scores(self) -> dict:
		scores = self.__calculate_scores()
		shared_score = scores['shared']
		individual_scores = scores['individual']

		player_results = []
		for uid, snapshot in self.snapshots.items():
			total_raw_score = shared_score + individual_scores.get(uid, 0.0)
			conversation_quality = (
				total_raw_score / self.conversation_length if self.conversation_length > 0 else 0
			)

			final_player_data = asdict(snapshot)
			final_player_data['scores'] = {
				'total': conversation_quality,
				'shared': shared_score,
				'individual': individual_scores.get(uid, 0.0),
			}

			player_results.append(final_player_data)

		shared_score_breakdown = {
			'total': scores['shared'],
			'importance': scores['importance'],
			'coherence': scores['coherence'],
			'freshness': scores['freshness'],
			'nonmonotonousness': scores['nonmonotonousness'],
		}

		return {
			'conversation_length': len(self.history),
			'pauses': self.history.count(None),
			'player_scores': player_results,
			'shared_score_breakdown': shared_score_breakdown,
		}

	def _calculate_turn_score_impact(self, item: Item | None) -> dict:
		if item is None:
			return {'total': 0.0}

		turn_idx = len(self.history) - 1
		impact = {}

		is_repeated = any(
			existing_item and existing_item.id == item.id for existing_item in self.history[:-1]
		)

		if is_repeated:
			impact['importance'] = 0.0
			impact['coherence'] = 0.0
			impact['freshness'] = 0.0
			impact['nonmonotonousness'] = self.__calculate_nonmonotonousness_score(
				turn_idx, item, repeated=True
			)
		else:
			impact['importance'] = item.importance
			impact['coherence'] = self.__calculate_coherence_score(turn_idx, item)
			impact['freshness'] = self.__calculate_freshness_score(turn_idx, item)
			impact['nonmonotonousness'] = self.__calculate_nonmonotonousness_score(
				turn_idx, item, repeated=False
			)

		speaker_id = self.last_player_id
		snapshot = self.snapshots.get(speaker_id, None)
		individual_bonus = 0.0
		if snapshot:
			preferences = snapshot.preferences
			bonuses = [
				1 - preferences.index(s) / len(preferences)
				for s in item.subjects
				if s in preferences
			]
			if bonuses:
				individual_bonus = sum(bonuses) / len(bonuses)
		impact['individual'] = individual_bonus
		impact['total'] = sum(
			v
			for k, v in impact.items()
			if k in ['importance', 'coherence', 'freshness', 'nonmonotonousness']
		)

		return impact

	def __turn(self):
		proposals = self.__get_proposals()
		speaker, item = self.__select_speaker(proposals)

		if speaker:
			self.history.append(item)
			self.last_player_id = speaker
			self.consecutive_pauses = 0
			self.player_contributions[speaker].append(item)
		else:
			self.history.append(None)
			self.last_player_id = None
			self.consecutive_pauses += 1

		self.turn += 1
		score_impact = self._calculate_turn_score_impact(item)
		return {
			'turn': self.turn,
			'speaker_id': speaker,
			'speaker_name': self.player_names.get(speaker, ''),
			'item': item,
			'proposals': proposals,
			'is_over': self.turn >= self.conversation_length or self.consecutive_pauses >= 3,
			'score_impact': score_impact,
		}

	def step(self) -> dict | None:
		if self.turn >= self.conversation_length or self.consecutive_pauses >= 3:
			return None

		return self.__turn()

	def run(self, players: list[type[Player]]):
		turn_impact = []

		while self.turn < self.conversation_length:
			impact = self.__turn()
			turn_impact.append(impact)

			if self.consecutive_pauses >= 3:
				break

		score_data = self.final_scores()

		output = {
			'history': self.history,
			'turn_impact': turn_impact,
			'score_breakdown': score_data['shared_score_breakdown'],
			'scores': score_data,
		}

		return output
