import json
import csv
import os
import uuid
from collections import defaultdict, Counter
from typing import Optional, Dict, List, Any

from models.item import Item


# Global float precision control for all formatted numeric outputs in this module
FLOAT_PRECISION = 4


class CustomEncoder(json.JSONEncoder):
	def _sanitize_keys(self, obj):
		if isinstance(obj, dict):
			return {str(k): self._sanitize_keys(v) for k, v in obj.items()}
		if isinstance(obj, list):
			return [self._sanitize_keys(elem) for elem in obj]
		return obj

	def default(self, obj):
		if isinstance(obj, Item):
			return {
				'id': str(obj.id),
				'player_id': str(obj.player_id),
				'importance': obj.importance,
				'subjects': obj.subjects,
			}
		if isinstance(obj, uuid.UUID):
			return str(obj)

		return super().default(obj)


	def iterencode(self, obj, _one_shot=False):
		# Sanitize dict keys before encoding to avoid UUID keys errors
		sanitized_obj = self._sanitize_keys(obj)
		return super().iterencode(sanitized_obj, _one_shot=_one_shot)


class ConversationAnalyzer:
	def __init__(self):
		pass
	def compute_round_averages(self, per_round_metrics: list[dict[str, float]]) -> dict[str, float]:
		"""Compute averages from a list of per-round metric dicts with keys:
		- quality_score, contributed_score, involvement_ratio
		Missing keys default to 0.0.
		"""
		if not per_round_metrics:
			return {
				'avg_score': 0.0,
				'avg_shared_score': 0.0,
				'avg_involvement_ratio': 0.0,
			}
		total_q = sum(m.get('quality_score', 0.0) for m in per_round_metrics)
		total_c = sum(m.get('contributed_score', 0.0) for m in per_round_metrics)
		total_i = sum(m.get('involvement_ratio', 0.0) for m in per_round_metrics)
		n = len(per_round_metrics)
		return {
			'avg_score': total_q / n if n else 0.0,
			'avg_shared_score': total_c / n if n else 0.0,
			'avg_involvement_ratio': total_i / n if n else 0.0,
		}

	def compute_type_averages(self, simulation_results: Dict[str, Any], engine=None) -> list[dict[str, Any]]:
		"""Compute per-type averages for CSV output.
		Returns list of rows with keys:
		- type, avg_score, avg_shared_score, avg_involvement_ratio,
		  importance, coherence, freshness, nonmonotone (normalized per turn)
		"""
		scores = simulation_results['scores']

		# Per-player contributed from speaking rounds
		per_player, per_type_contribs, _, per_type_counts = self._aggregate_speaking_contributions(simulation_results, engine)

		# Gather per-type player lists for averaging player-based metrics
		type_to_players: Dict[str, list[int]] = defaultdict(list)
		for i, player_result in enumerate(scores['player_scores']):
			ptype = type(engine.players[i]).__name__ if engine else 'Unknown'
			type_to_players[ptype].append(i)

		rows: list[dict[str, Any]] = []
		for ptype, indices in type_to_players.items():
			if not indices:
				continue
			# conversation length for normalization
			conversation_length = scores.get('conversation_length', len(simulation_results.get('history', [])))
			L = max(1, conversation_length)
			# Average of player quality scores in this type (already normalized by Engine)
			score_avg = sum(float(scores['player_scores'][i]['scores']['total']) for i in indices) / len(indices)
			# Average of individual scores in this type, normalized by L
			individual_avg = sum(float(scores['player_scores'][i]['scores']['individual']) / L for i in indices) / len(indices)
			# Average of shared scores in this type, normalized by L (use Engine's shared total)
			shared_avg = sum(float(scores['player_scores'][i]['scores']['shared']) / L for i in indices) / len(indices)
			# Average involvement ratio per player in this type (unchanged definition)
			# Use conversation-level normalization for participation expectation
			conversation_length = scores.get('conversation_length', len(simulation_results.get('history', [])))
			total_participants = len(scores['player_scores'])
			contrib_counts = [len(engine.player_contributions.get(engine.players[i].id, [])) if engine else 0 for i in indices]
			involvements = []
			for c in contrib_counts:
				if conversation_length > 0 and total_participants > 0:
					involvements.append((c / conversation_length) * total_participants)
				else:
					involvements.append(0.0)
			involvement_avg = sum(involvements) / len(involvements) if involvements else 0.0

			# Attribute contributions per type normalized by number of speaking turns for that type
			contribs = per_type_contribs.get(ptype, {}) or {}
			type_speaking_turns = max(1, per_type_counts.get(ptype, 0))
			row = {
				'type': ptype,
				'score': score_avg,
				'individual': individual_avg,
				'shared_score': shared_avg,
				'involvement_ratio': involvement_avg,
				'contributed_individual_score': float(contribs.get('individual_total', 0.0)) / type_speaking_turns,
				'contributed_shared_score': float(contribs.get('shared_total', 0.0)) / type_speaking_turns,
				'importance': float(contribs.get('importance', 0.0)) / type_speaking_turns,
				'coherence': float(contribs.get('coherence', 0.0)) / type_speaking_turns,
				'freshness': float(contribs.get('freshness', 0.0)) / type_speaking_turns,
				'nonmonotone': float(contribs.get('nonmonotonousness', 0.0)) / type_speaking_turns,
				'player_numbers': len(indices),
			}
			rows.append(row)

		# Sort rows by avg_score descending
		rows.sort(key=lambda r: r['score'], reverse=True)
		return rows
	
	def _aggregate_speaking_contributions(self, simulation_results: Dict[str, Any], engine=None):
		"""Aggregate shared score components only from speaking turns per player and per type.
		Recalculate per-turn impacts using the FINAL conversation history so that
		future-aware coherence is reflected. Normalize later by speaking counts.
		Returns: per_player, per_type, per_player_counts, per_type_counts
		"""
		per_player: Dict[Any, Dict[str, float]] = {}
		per_type: Dict[str, Dict[str, float]] = {}
		per_player_counts: Dict[Any, int] = {}
		per_type_counts: Dict[str, int] = {}

		# Map player id -> type name
		id_to_type: Dict[Any, str] = {}
		if engine:
			for p in engine.players:
				id_to_type[p.id] = type(p).__name__

		# Recompute per-turn contributions using final history
		final_history = list(getattr(engine, 'history', [])) if engine else []
		unique_seen: set = set()
		turn_impacts = simulation_results.get('turn_impact', [])
		for idx, turn in enumerate(turn_impacts):
			speaker_id = turn.get('speaker_id')
			if not speaker_id:
				continue
			if idx >= len(final_history):
				continue
			item = final_history[idx]
			if item is None:
				continue

			# Determine repeated relative to prior occurrences in final history
			repeated = getattr(item, 'id', None) in unique_seen
			if getattr(item, 'id', None) is not None and not repeated:
				unique_seen.add(item.id)

			# Use Engine's scoring functions to match final breakdown
			if engine:
				imp = 0.0 if repeated else float(getattr(item, 'importance', 0.0))
				coh = 0.0 if repeated else float(engine._Engine__calculate_coherence_score(idx, item))
				fre = 0.0 if repeated else float(engine._Engine__calculate_freshness_score(idx, item))
				non = float(engine._Engine__calculate_nonmonotonousness_score(idx, item, repeated))
				# Individual bonus at speaking time (consistent with Engine)
				preferences = engine.snapshots.get(speaker_id).preferences if engine else []
				bonuses = [1 - preferences.index(s) / len(preferences) for s in item.subjects if s in preferences] if preferences else []
				ind = float(sum(bonuses) / len(bonuses)) if bonuses else 0.0
			else:
				imp = getattr(item, 'importance', 0.0)
				coh = 0.0
				fre = 0.0
				non = 0.0
				ind = 0.0

			shared_total = imp + coh + fre + non

			if speaker_id not in per_player:
				per_player[speaker_id] = {
					'shared_total': 0.0,
					'importance': 0.0,
					'coherence': 0.0,
					'freshness': 0.0,
					'nonmonotonousness': 0.0,
					'individual_total': 0.0,
				}
				per_player_counts[speaker_id] = 0
			pp = per_player[speaker_id]
			pp['shared_total'] += shared_total
			pp['importance'] += imp
			pp['coherence'] += coh
			pp['freshness'] += fre
			pp['nonmonotonousness'] += non
			pp['individual_total'] += ind
			per_player_counts[speaker_id] += 1

			type_name = id_to_type.get(speaker_id, 'Unknown')
			if type_name not in per_type:
				per_type[type_name] = {
					'shared_total': 0.0,
					'importance': 0.0,
					'coherence': 0.0,
					'freshness': 0.0,
					'nonmonotonousness': 0.0,
					'individual_total': 0.0,
				}
				per_type_counts[type_name] = 0
			pt = per_type[type_name]
			pt['shared_total'] += shared_total
			pt['importance'] += imp
			pt['coherence'] += coh
			pt['freshness'] += fre
			pt['nonmonotonousness'] += non
			pt['individual_total'] += ind
			per_type_counts[type_name] += 1

		return per_player, per_type, per_player_counts, per_type_counts

	
	def raw_data_to_human_readable(self, simulation_results: Dict[str, Any], engine=None, test_player: Optional[str] = None) -> str:
		"""
		Convert raw simulation results to human-readable analysis report.
		
		Args:
			simulation_results: Results from engine.run()
			engine: Engine instance to get player types and contributions
			test_player: Name of test player (will be marked with "(test)")
		"""
		output = []
		output.append("CONVERSATION ANALYSIS REPORT")
		output.append("=" * 60)
		output.append("")
		
		# Individual Players Analysis
		individual_analysis = self._analyze_individual_players(simulation_results, engine, test_player)
		output.append(individual_analysis)
		output.append("")
		output.append("")
		
		# Player Types Analysis
		if engine:
			type_analysis = self._analyze_player_types(simulation_results, engine)
			output.append(type_analysis)
			output.append("")
			output.append("")
		
		# Global Metrics Analysis
		global_analysis = self._analyze_global_metrics(simulation_results)
		output.append(global_analysis)
		
		return "\n".join(output)
	
	def raw_data_to_csv(self, simulation_results: Dict[str, Any], engine=None, test_player: Optional[str] = None, csv_path: Optional[str] = None) -> str:
		"""
		Export per-player metrics to CSV.

		Columns:
		- player: player identifier
		- score: overall quality score (descending rank basis)
		- rank: rank by score (1 = best)
		- shared_score: contributed/shared score
		- involvement_ratio: n / L * p where n=contributions, L=conversation length, p=participants

		Args:
			simulation_results: Results from engine.run()
			engine: Engine instance to get player names and contributions
			test_player: Name prefix of test player (optional label)
			csv_path: Output CSV path. Defaults to "results/player_metrics.csv".

		Returns:
			Path to the written CSV file.
		"""
		# Defaults
		if csv_path is None:
			csv_path = "results/player_metrics.csv"

		scores = simulation_results['scores']
		conversation_length = scores.get('conversation_length', len(simulation_results.get('history', [])))
		total_participants = len(scores['player_scores']) if scores.get('player_scores') else 0

		# Collect per-player data
		players_data: list[dict[str, Any]] = []
		per_player, _, _, _ = self._aggregate_speaking_contributions(simulation_results, engine)
		type_counters = defaultdict(int)
		for i, player_result in enumerate(scores['player_scores']):
			if engine:
				player_type = type(engine.players[i]).__name__
				type_counters[player_type] += 1
				player_name = f"{player_type}_{type_counters[player_type]}"
				contributions = len(engine.player_contributions.get(engine.players[i].id, []))
			else:
				player_name = f"Player_{i+1}"
				contributions = 0

			if test_player and player_name.startswith(test_player):
				player_name += " (test)"

			quality_score = float(player_result['scores']['total'])
			pid = engine.players[i].id if engine else None
			contributed_score = float((per_player.get(pid, {}) or {}).get('shared_total', 0.0))
			if conversation_length > 0 and total_participants > 0:
				involvement_ratio = (contributions / conversation_length) * total_participants
			else:
				involvement_ratio = 0.0

			players_data.append({
				'name': player_name,
				'quality_score': quality_score,
				'contributed_score': contributed_score,
				'involvement_ratio': float(involvement_ratio),
				'contributions': contributions,
			})

		# Compute per-type averages and write CSV
		rows = self.compute_type_averages(simulation_results, engine)
		os.makedirs(os.path.dirname(csv_path) or '.', exist_ok=True)
		with open(csv_path, 'w', newline='') as f:
			writer = csv.writer(f)
			writer.writerow(["type", "player_numbers", "score", "individual", "shared_score", "involvement_ratio", "contributed_individual_score", "contributed_shared_score", "importance", "coherence", "freshness", "nonmonotone"])
			for r in rows:
				writer.writerow([
					r['type'],
					r['player_numbers'],
					f"{r['score']:.{FLOAT_PRECISION}f}",
					f"{r['individual']:.{FLOAT_PRECISION}f}",
					f"{r['shared_score']:.{FLOAT_PRECISION}f}",
					f"{r['involvement_ratio']:.{FLOAT_PRECISION}f}",
					f"{r['contributed_individual_score']:.{FLOAT_PRECISION}f}",
					f"{r['contributed_shared_score']:.{FLOAT_PRECISION}f}",
					f"{r['importance']:.{FLOAT_PRECISION}f}",
					f"{r['coherence']:.{FLOAT_PRECISION}f}",
					f"{r['freshness']:.{FLOAT_PRECISION}f}",
					f"{r['nonmonotone']:.{FLOAT_PRECISION}f}",
				])

		return csv_path
	
	def _analyze_individual_players(self, simulation_results: Dict[str, Any], engine=None, test_player: Optional[str] = None) -> str:
		"""Create detailed table of individual player performance."""
		output = []
		output.append("INDIVIDUAL PLAYER ANALYSIS")
		output.append("-" * 40)
		
		conversation_length = simulation_results['scores'].get('conversation_length', len(simulation_results.get('history', [])))
		total_participants = len(simulation_results['scores']['player_scores'])
		
		# Prepare player data
		player_data = []
		per_player, _, _, _ = self._aggregate_speaking_contributions(simulation_results, engine)
		type_counters = defaultdict(int)
		for i, player_result in enumerate(simulation_results['scores']['player_scores']):
			if engine:
				player_type = type(engine.players[i]).__name__
				type_counters[player_type] += 1
				player_name = f"{player_type}_{type_counters[player_type]}"
				
				# Calculate involvement rate
				contributions = len(engine.player_contributions.get(engine.players[i].id, []))
			else:
				player_name = f"Player_{i+1}"
				contributions = 0
			
			# Mark test player
			if test_player and player_name.startswith(test_player):
				player_name += " (test)"
			
			involvement_rate = self._calculate_involvement_rate(contributions, conversation_length, total_participants)
			
			# Contributed/shared score only from speaking rounds
			pid = engine.players[i].id if engine else None
			contrib_shared = (per_player.get(pid, {}) or {}).get('shared_total', 0.0)
			player_data.append({
				'name': player_name,
				'quality_score': player_result['scores']['total'],
				'individual_score': player_result['scores']['individual'],
				'contributed_score': contrib_shared,
				'involvement_rate': involvement_rate,
				'contributions': contributions
			})
		
		# Sort by quality score (descending)
		player_data.sort(key=lambda x: x['quality_score'], reverse=True)
		
		# Format table
		table = self._format_player_table(player_data)
		output.extend(table)
		
		return "\n".join(output)
	
	def _analyze_player_types(self, simulation_results: Dict[str, Any], engine) -> str:
		"""Analyze performance by player type with rankings."""
		output = []
		output.append("PLAYER TYPE ANALYSIS")
		output.append("-" * 30)
		
		conversation_length = simulation_results['scores'].get('conversation_length', len(simulation_results.get('history', [])))
		total_participants = len(simulation_results['scores']['player_scores'])
		
		# Group data by player type using speaking-round contributions
		per_player, per_type_contribs, _, _ = self._aggregate_speaking_contributions(simulation_results, engine)
		type_data = defaultdict(list)
		for i, player_result in enumerate(simulation_results['scores']['player_scores']):
			player_type = type(engine.players[i]).__name__
			pid = engine.players[i].id
			contributions = len(engine.player_contributions.get(pid, []))
			involvement_rate = self._calculate_involvement_rate(contributions, conversation_length, total_participants)

			contrib_shared = (per_player.get(pid, {}) or {}).get('shared_total', 0.0)
			type_data[player_type].append({
				'quality_score': player_result['scores']['total'],
				'individual_score': player_result['scores']['individual'],
				'contributed_score': contrib_shared,
				'involvement_rate': involvement_rate,
				'contributions': contributions
			})
		
		# Calculate averages for each type
		type_averages = []
		for player_type, players in type_data.items():
			avg_data = {
				'type': player_type,
				'count': len(players),
				'avg_quality_score': sum(p['quality_score'] for p in players) / len(players),
				'avg_individual_score': sum(p['individual_score'] for p in players) / len(players),
				'avg_contributed_score': sum(p['contributed_score'] for p in players) / len(players),
				'avg_involvement_rate': sum(p['involvement_rate'] for p in players) / len(players),
				'total_contributions': sum(p['contributions'] for p in players)
			}
			type_averages.append(avg_data)
		
		# Sort by average quality score
		type_averages.sort(key=lambda x: x['avg_quality_score'], reverse=True)
		
		# Add rankings
		for rank, type_avg in enumerate(type_averages, 1):
			type_avg['rank'] = rank
		
		# Format type analysis table
		table = self._format_type_table(type_averages)
		output.extend(table)
		
		# Normalized attribute analysis (by speaking-round contributions per type)
		output.append("")
		output.append("NORMALIZED ATTRIBUTE ANALYSIS BY TYPE:")
		output.append("-" * 45)
		
		norm_factor = conversation_length if conversation_length > 0 else 1
		attr_data = []
		for type_avg in type_averages:
			ctype = type_avg['type']
			contribs = per_type_contribs.get(ctype, {}) or {}
			attr_data.append({
				'type': ctype,
				'norm_importance': float(contribs.get('importance', 0.0)) / norm_factor,
				'norm_coherence': float(contribs.get('coherence', 0.0)) / norm_factor,
				'norm_freshness': float(contribs.get('freshness', 0.0)) / norm_factor,
				'norm_nonmonotone': float(contribs.get('nonmonotonousness', 0.0)) / norm_factor
			})
		
		attr_table = self._format_attribute_table(attr_data)
		output.extend(attr_table)
		
		return "\n".join(output)
	
	def _analyze_global_metrics(self, simulation_results: Dict[str, Any]) -> str:
		"""Analyze global conversation metrics."""
		output = []
		output.append("GLOBAL CONVERSATION METRICS")
		output.append("-" * 35)
		
		scores = simulation_results['scores']
		shared_scores = scores['shared_score_breakdown']
		conversation_length = scores.get('conversation_length', len(simulation_results.get('history', [])))
		pauses = scores.get('pauses', 0)
		
		# Overall metrics
		output.append(f"Conversation Length: {conversation_length}")
		output.append(f"Total Pauses: {pauses}")
		output.append(f"Active Turns: {conversation_length - pauses}")
		output.append("")
		
		# Overall scores
		output.append("OVERALL SCORES:")
		output.append(f"  Total Shared Score: {shared_scores['total']:.{FLOAT_PRECISION}f}")
		output.append("")
		
		# Normalized scores
		norm_factor = conversation_length if conversation_length > 0 else 1
		output.append("NORMALIZED SCORES (per turn):")
		output.append(f"  Normalized Total: {shared_scores['total'] / norm_factor:.{FLOAT_PRECISION}f}")
		output.append(f"  Normalized Importance: {shared_scores['importance'] / norm_factor:.{FLOAT_PRECISION}f}")
		output.append(f"  Normalized Coherence: {shared_scores['coherence'] / norm_factor:.{FLOAT_PRECISION}f}")
		output.append(f"  Normalized Freshness: {shared_scores['freshness'] / norm_factor:.{FLOAT_PRECISION}f}")
		output.append(f"  Normalized Nonmonotonousness: {shared_scores['nonmonotonousness'] / norm_factor:.{FLOAT_PRECISION}f}")
		output.append("")
		
		# Player performance summary
		player_scores = [p['scores']['total'] for p in scores['player_scores']]
		output.append("PLAYER PERFORMANCE SUMMARY:")
		output.append(f"  Average Quality Score: {sum(player_scores) / len(player_scores):.{FLOAT_PRECISION}f}")
		output.append(f"  Best Quality Score: {max(player_scores):.{FLOAT_PRECISION}f}")
		output.append(f"  Worst Quality Score: {min(player_scores):.{FLOAT_PRECISION}f}")
		output.append(f"  Quality Score Std Dev: {self._calculate_std_dev(player_scores):.{FLOAT_PRECISION}f}")
		
		return "\n".join(output)
	
	def _calculate_involvement_rate(self, contributions: int, conversation_length: int, total_participants: int) -> float:
		"""Calculate involvement rate as participation / (conversation_length / total_participants)."""
		if conversation_length == 0 or total_participants == 0:
			return 0.0
		expected_participation = conversation_length / total_participants
		return contributions / expected_participation if expected_participation > 0 else 0.0
	
	def _format_player_table(self, player_data: List[Dict]) -> List[str]:
		"""Format individual player analysis table."""
		output = []
		
		# Header (center alignment)
		header_line = f"{'Player':^25} {'Quality':^12} {'Individual':^12} {'Contributed':^12} {'Involvement':^12} {'Num':^8}"
		output.append(header_line)
		output.append("-" * len(header_line))
		
		# Data rows
		for player in player_data:
			line = (f"{player['name']:^25} "
					f"{player['quality_score']:^12.{FLOAT_PRECISION}f} "
					f"{player['individual_score']:^12.{FLOAT_PRECISION}f} "
					f"{player['contributed_score']:^12.{FLOAT_PRECISION}f} "
					f"{player['involvement_rate']:^12.{FLOAT_PRECISION}f} "
					f"{player['contributions']:^8}")
			output.append(line)
		
		return output
	
	def _format_type_table(self, type_data: List[Dict]) -> List[str]:
		"""Format player type analysis table."""
		output = []
		
		# Header (center alignment)
		header_line = f"{'Rank':^6} {'Type':^20} {'Count':^7} {'Avg Qual':^10} {'Avg Indiv':^10} {'Avg Cont':^10} {'Avg Invol':^10} {'Total':^7}"
		output.append(header_line)
		output.append("-" * len(header_line))
		
		# Data rows
		for type_avg in type_data:
			line = (f"{type_avg['rank']:^6} "
					f"{type_avg['type']:^20} "
					f"{type_avg['count']:^7} "
					f"{type_avg['avg_quality_score']:^10.{FLOAT_PRECISION}f} "
					f"{type_avg['avg_individual_score']:^10.{FLOAT_PRECISION}f} "
					f"{type_avg['avg_contributed_score']:^10.{FLOAT_PRECISION}f} "
					f"{type_avg['avg_involvement_rate']:^10.{FLOAT_PRECISION}f} "
					f"{type_avg['total_contributions']:^7}")
			output.append(line)
		
		return output
	
	def _format_attribute_table(self, attr_data: List[Dict]) -> List[str]:
		"""Format normalized attribute analysis table."""
		output = []
		
		# Header (center alignment)
		header_line = f"{'Type':^20} {'Importance':^12} {'Coherence':^12} {'Freshness':^12} {'Nonmonotone':^12}"
		output.append(header_line)
		output.append("-" * len(header_line))
		
		# Data rows
		for attr in attr_data:
			line = (f"{attr['type']:^20} "
					f"{attr['norm_importance']:^12.{FLOAT_PRECISION}f} "
					f"{attr['norm_coherence']:^12.{FLOAT_PRECISION}f} "
					f"{attr['norm_freshness']:^12.{FLOAT_PRECISION}f} "
					f"{attr['norm_nonmonotone']:^12.{FLOAT_PRECISION}f}")
			output.append(line)
		
		return output
	
	def _calculate_std_dev(self, values: List[float]) -> float:
		"""Calculate standard deviation of a list of values."""
		if len(values) < 2:
			return 0.0
		mean = sum(values) / len(values)
		variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
		return variance ** 0.5


class ConversationScorer:
	"""Handles all score calculations for conversation items."""
	
	def __init__(self, player_preferences: list[int]):
		self.player_preferences = player_preferences

	def is_repeated(self, item: Item, history: list[Item]) -> bool:
		"""Check if item was already used in conversation."""
		return any(existing_item and existing_item.id == item.id for existing_item in history)

	def calculate_freshness_score(self, item: Item, position: int, history: list[Item]) -> float:
		"""Calculate freshness score (based on Engine's logic)."""
		if position == 0 or history[position - 1] is not None:
			return 0.0

		prior_items = (item for item in history[max(0, position - 6) : position - 1] if item is not None)
		prior_subjects = {s for item in prior_items for s in item.subjects}

		novel_subjects = [s for s in item.subjects if s not in prior_subjects]
		return float(len(novel_subjects))

	def calculate_coherence_score(self, item: Item, position: int, history: list[Item]) -> float:
		"""Calculate coherence score (based on Engine's logic)."""
		context_items = []

		for j in range(position - 1, max(-1, position - 4), -1):
			if history[j] is None:
				break
			context_items.append(history[j])

		# For future context, we can't know what comes next, so skip

		context_subject_counts = Counter(s for item in context_items for s in item.subjects)
		score = 0.0

		if not all(subject in context_subject_counts for subject in item.subjects):
			score -= 1.0

		if all(context_subject_counts.get(s, 0) >= 2 for s in item.subjects):
			score += 1.0

		return score

	def calculate_nonmonotonousness_score(self, item: Item, position: int, history: list[Item], repeated: bool) -> float:
		"""Calculate nonmonotonousness score (based on Engine's logic)."""
		if repeated:
			return -1.0

		if position < 3:
			return 0.0

		last_three_items = [history[j] for j in range(position - 3, position)]
		if all(
			item and any(s in item.subjects for s in item.subjects)
			for item in last_three_items
		):
			return -1.0

		return 0.0

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

		# Shared score components (based on Engine's _calculate_turn_score_impact)
		if is_repeated:
			importance = 0.0
			coherence = 0.0
			freshness = 0.0
		else:
			importance = item.importance
			coherence = self.calculate_coherence_score(item, position, history)
			freshness = self.calculate_freshness_score(item, position, history)

		nonmonotonousness = self.calculate_nonmonotonousness_score(item, position, history, is_repeated)
		
		# Individual score
		individual = self.calculate_individual_score(item)

		# Total shared score
		shared_total = importance + coherence + freshness + nonmonotonousness
		return shared_total

	def calculate_total_score(self, item: Item, history: list[Item]) -> float:
		"""Calculate total score impact for adding this item (replicating Engine logic)."""

		
		# Individual score
		individual = self.calculate_individual_score(item)

		# Total shared score
		shared_total = self.calculate_shared_score(item, history)
  
		return shared_total + individual

