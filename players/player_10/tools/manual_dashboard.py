"""Generate a dashboard for manual engine experiments.

This script recreates two lightweight experiment profiles (balanced vs adversarial
supporting casts) across a small set of seeds and toggles Player10's altruism
probability. The per-run outputs are converted into the same shape that the
Plotly dashboard expects, so we can reuse generate_dashboard without relying
on the MonteCarlo simulator assets that aren't available locally.
"""

from __future__ import annotations

import json
import statistics as stats
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.append(str(PROJECT_ROOT))


@dataclass
class ManualConfig:
	"""Minimal config stub exposing the knobs used by the dashboard helpers."""

	altruism_prob: float
	tau_margin: float
	epsilon_fresh: float
	epsilon_mono: float
	seed: int
	players: dict[str, int]
	subjects: int
	memory_size: int
	conversation_length: int
	min_samples_pid: int
	ewma_alpha: float
	importance_weight: float
	coherence_weight: float
	freshness_weight: float
	monotony_weight: float


@dataclass
class ManualResult:
	"""Container that matches the attributes accessed by the dashboard builder."""

	config: ManualConfig
	total_score: float
	best_total_score: float
	player_scores: dict[str, float]
	player_contributions: dict[str, int]
	conversation_length: int
	early_termination: bool
	pause_count: int
	unique_items_used: int
	execution_time: float
	score_breakdown: dict[str, float]
	player_metrics: dict[str, dict[str, float | str | int | None]]
	player10_total_mean: float
	player10_individual_mean: float
	player10_rank_mean: float
	player10_gap_to_best: float
	player10_instances: int


def _build_label_map(engine: Any) -> dict[str, str]:
	"""Assign stable human-readable labels to player UUIDs."""
	counts: Counter[str] = Counter()
	labels: dict[str, str] = {}

	for player in engine.players:
		class_name = type(player).__name__
		if class_name == 'Player10Agent':
			label = 'Player10'
		else:
			counts[class_name] += 1
			label = f'{class_name}#{counts[class_name]}'
		labels[str(player.id)] = label

	return labels


def _rank_players(totals: dict[str, float]) -> dict[str, float]:
	"""Return 1-based ranks (dense ranking) for each player label."""
	sorted_totals = sorted(totals.items(), key=lambda item: item[1], reverse=True)
	ranks: dict[str, float] = {}

	current_rank = 1
	previous_value: float | None = None

	for index, (label, value) in enumerate(sorted_totals, start=1):
		if previous_value is None or value < previous_value:
			current_rank = index
		previous_value = value
		ranks[label] = float(current_rank)

	return ranks


def _build_manual_result(
	engine: Any,
	seed: int,
	altruism: float,
	roster: Sequence[type],
	subjects: int,
	memory_size: int,
	conversation_length: int,
) -> ManualResult:
	"""Run the engine once and transform the output into a dashboard result."""
	from players.player_10.agent import config as p10_config

	output = engine.run(list(roster))
	history = output['history']
	scores = output['scores']

	label_map = _build_label_map(engine)

	player_scores_dict: dict[str, float] = {}
	player_metrics: dict[str, dict[str, float | str | int | None]] = {}

	totals_for_ranking: dict[str, float] = {}

	for entry in scores['player_scores']:
		label = label_map[str(entry['id'])]
		total = float(entry['scores']['total'])
		individual = float(entry['scores']['individual'])
		shared = float(entry['scores']['shared'])

		player_scores_dict[label] = total
		player_metrics[label] = {
			'class_name': label.split('#')[0],
			'alias': label,
			'total': total,
			'individual': individual,
			'shared': shared,
			'rank': None,  # filled in after ranking
		}
		totals_for_ranking[label] = total

	ranks = _rank_players(totals_for_ranking)
	for label, rank in ranks.items():
		player_metrics[label]['rank'] = rank

	player10_total = player_scores_dict['Player10']
	best_total = max(player_scores_dict.values())

	player_contributions_counts = {
		label_map[str(uid)]: len(items) for uid, items in engine.player_contributions.items()
	}

	unique_items = {item.id for item in history if item is not None}
	pause_count = sum(1 for item in history if item is None)

	config = ManualConfig(
		altruism_prob=altruism,
		tau_margin=p10_config.TAU_MARGIN,
		epsilon_fresh=p10_config.EPSILON_FRESH,
		epsilon_mono=p10_config.EPSILON_MONO,
		seed=seed,
		players=dict(Counter(type(player).__name__ for player in engine.players)),
		subjects=subjects,
		memory_size=memory_size,
		conversation_length=conversation_length,
		min_samples_pid=p10_config.MIN_SAMPLES_PID,
		ewma_alpha=p10_config.EWMA_ALPHA,
		importance_weight=p10_config.IMPORTANCE_WEIGHT,
		coherence_weight=p10_config.COHERENCE_WEIGHT,
		freshness_weight=p10_config.FRESHNESS_WEIGHT,
		monotony_weight=p10_config.MONOTONY_WEIGHT,
	)

	return ManualResult(
		config=config,
		total_score=float(output['score_breakdown']['total']),
		best_total_score=best_total,
		player_scores=player_scores_dict,
		player_contributions=player_contributions_counts,
		conversation_length=len(history),
		early_termination=len(history) < conversation_length,
		pause_count=pause_count,
		unique_items_used=len(unique_items),
		execution_time=0.0,
		score_breakdown={k: float(v) for k, v in output['score_breakdown'].items()},
		player_metrics=player_metrics,
		player10_total_mean=player10_total,
		player10_individual_mean=float(
			next(
				entry['scores']['individual']
				for entry in scores['player_scores']
				if label_map[str(entry['id'])] == 'Player10'
			)
		),
		player10_rank_mean=ranks['Player10'],
		player10_gap_to_best=best_total - player10_total,
		player10_instances=1,
	)


def run_manual_experiments() -> tuple[list[ManualResult], dict[str, dict[str, float]]]:
	"""Return all per-run results plus an aggregate summary per configuration."""
	from core.engine import Engine
	from players.pause_player import PausePlayer
	from players.player_10.agent import config as p10_config
	from players.player_10.agent.player import Player10Agent
	from players.random_pause_player import RandomPausePlayer
	from players.random_player import RandomPlayer

	subjects = 10
	memory_size = 16
	conversation_length = 40
	seeds = list(range(100, 116))

	rosters: dict[str, Sequence[type]] = {
		'Balanced support (3 Random)': [Player10Agent, RandomPlayer, RandomPlayer, RandomPlayer],
		'Adversarial mix (Random, RandomPause, Pause)': [
			Player10Agent,
			RandomPlayer,
			RandomPausePlayer,
			PausePlayer,
		],
	}

	results: list[ManualResult] = []
	aggregates: dict[str, list[float]] = {}

	original_altruism = p10_config.ALTRUISM_USE_PROB

	for roster_name, roster in rosters.items():
		for altruism_value in (0.0, 0.6):
			p10_config.ALTRUISM_USE_PROB = altruism_value

			key = f'{roster_name} | altruism={altruism_value:.1f}'
			aggregates[key] = []

			for seed in seeds:
				engine = Engine(
					players=list(roster),
					player_count=len(roster),
					subjects=subjects,
					memory_size=memory_size,
					conversation_length=conversation_length,
					seed=seed,
				)
				result = _build_manual_result(
					engine,
					seed=seed,
					altruism=altruism_value,
					roster=roster,
					subjects=subjects,
					memory_size=memory_size,
					conversation_length=conversation_length,
				)
				results.append(result)
				aggregates[key].append(result.total_score)

	# Restore the original altruism probability so we do not affect other tooling
	p10_config.ALTRUISM_USE_PROB = original_altruism

	aggregate_summary = {
		key: {
			'mean': stats.mean(values),
			'std': stats.pstdev(values) if len(values) > 1 else 0.0,
		}
		for key, values in aggregates.items()
	}

	output_payload = [
		{
			'config': asdict(result.config),
			'total_score': result.total_score,
			'best_total_score': result.best_total_score,
			'player_scores': result.player_scores,
			'player_contributions': result.player_contributions,
			'conversation_length': result.conversation_length,
			'early_termination': result.early_termination,
			'pause_count': result.pause_count,
			'unique_items_used': result.unique_items_used,
			'execution_time': result.execution_time,
			'score_breakdown': result.score_breakdown,
			'player_metrics': result.player_metrics,
			'player10_total_mean': result.player10_total_mean,
			'player10_individual_mean': result.player10_individual_mean,
			'player10_rank_mean': result.player10_rank_mean,
			'player10_gap_to_best': result.player10_gap_to_best,
			'player10_instances': result.player10_instances,
			'altruism_prob': result.config.altruism_prob,
			'seed': result.config.seed,
			'players': result.config.players,
		}
		for result in results
	]

	output_path_json = Path('players/player_10/results/manual_dashboard_runs.json')
	output_path_json.write_text(json.dumps(output_payload, indent=2))
	print(f'Detailed run data written to {output_path_json}')

	return results, aggregate_summary


def main(open_browser: bool = False) -> None:
	from players.player_10.tools.dashboard import generate_dashboard

	results, summary = run_manual_experiments()

	analysis = {
		'total_simulations': len(results),
		'unique_configurations': len(summary),
		'best_configurations': [
			{
				'label': label,
				'mean_score': stats['mean'],
				'std_score': stats['std'],
			}
			for label, stats in sorted(
				summary.items(), key=lambda item: item[1]['mean'], reverse=True
			)
		],
	}

	dashboard_config = SimpleNamespace(
		name='Manual Engine Experiments',
		description='Player10 altruism sensitivity across two roster archetypes.',
		output_dir='players/player_10/results',
	)

	output_path = generate_dashboard(
		results,
		analysis,
		dashboard_config,
		output_dir='players/player_10/results/dashboards',
		open_browser=open_browser,
	)

	if output_path:
		print(f'Dashboard written to: {output_path}')
	else:
		print('Plotly is not installed; dashboard generation skipped.')


if __name__ == '__main__':
	main(open_browser=False)
