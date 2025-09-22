"""
Monte Carlo simulation framework for testing Player10 strategies.

This module provides tools to run multiple simulations with different parameterizations
and analyze the results to find optimal strategy configurations.
"""

import json
import random
import time
from collections import defaultdict
<<<<<<< HEAD
from dataclasses import asdict, dataclass, field
from importlib import import_module
=======
from dataclasses import asdict, dataclass
>>>>>>> lsig/main
from pathlib import Path
from typing import Any

from core.engine import Engine
from models.player import Player

from ..agent.config import (
	COHERENCE_WEIGHT,
	EWMA_ALPHA,
	FRESHNESS_WEIGHT,
	IMPORTANCE_WEIGHT,
	MIN_SAMPLES_PID,
	MONOTONY_WEIGHT,
)
<<<<<<< HEAD
=======
from ..agent.player import Player10
>>>>>>> lsig/main


@dataclass
class SimulationConfig:
	"""Configuration for a single simulation run."""

	altruism_prob: float
	tau_margin: float
	epsilon_fresh: float
	epsilon_mono: float
	seed: int
	players: dict[str, int]
	subjects: int = 20
	memory_size: int = 10
	conversation_length: int = 50
	# Extended config knobs (defaults pulled from agent.config)
	min_samples_pid: int = MIN_SAMPLES_PID
	ewma_alpha: float = EWMA_ALPHA
	importance_weight: float = IMPORTANCE_WEIGHT
	coherence_weight: float = COHERENCE_WEIGHT
	freshness_weight: float = FRESHNESS_WEIGHT
	monotony_weight: float = MONOTONY_WEIGHT


@dataclass
class SimulationResult:
	"""Results from a single simulation run."""

	config: SimulationConfig
	total_score: float
	player_scores: dict[str, float]
	player_contributions: dict[str, int]
	conversation_length: int
	early_termination: bool
	pause_count: int
	unique_items_used: int
	execution_time: float
<<<<<<< HEAD
	score_breakdown: dict[str, float] = field(default_factory=dict)
	player_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
	player10_total_mean: float | None = None
	player10_individual_mean: float | None = None
	player10_rank_mean: float | None = None
	player10_instances: int = 0
	best_total_score: float = 0.0
	player10_gap_to_best: float | None = None
=======
>>>>>>> lsig/main


class MonteCarloSimulator:
	"""Monte Carlo simulator for testing Player10 strategies."""

<<<<<<< HEAD
	def __init__(self, output_dir: str = 'players/player_10/results'):
		self.output_dir = Path(output_dir)
		self.output_dir.mkdir(exist_ok=True)
		self.results: list[SimulationResult] = []
		self.last_metadata: dict[str, Any] = {}
=======
	def __init__(self, output_dir: str = 'simulation_results'):
		self.output_dir = Path(output_dir)
		self.output_dir.mkdir(exist_ok=True)
		self.results: list[SimulationResult] = []
>>>>>>> lsig/main

	def run_single_simulation(self, config: SimulationConfig) -> SimulationResult:
		"""
		Run a single simulation with the given configuration.

		Args:
			config: Configuration for the simulation

		Returns:
			Results from the simulation
		"""
		start_time = time.time()

		# Set random seed for reproducibility
		random.seed(config.seed)

		# Temporarily update Player10 config
		self._update_player10_config(config)

		try:
<<<<<<< HEAD
			# Create players and track metadata for post-run analysis
			players, player_meta = self._create_players(config.players)
=======
			# Create players
			players = self._create_players(config.players)
>>>>>>> lsig/main

			# Create engine
			engine = Engine(
				players=players,
				player_count=sum(config.players.values()),
				subjects=config.subjects,
				memory_size=config.memory_size,
				conversation_length=config.conversation_length,
				seed=config.seed,
			)

			# Run simulation
			simulation_results = engine.run(players)

			# Extract results
<<<<<<< HEAD
			result = self._extract_results(
				config, simulation_results, time.time() - start_time, player_meta
			)
=======
			result = self._extract_results(config, simulation_results, time.time() - start_time)
>>>>>>> lsig/main

			return result

		finally:
			# Reset config to original values
			self._reset_player10_config()

	def run_parameter_sweep(
		self,
		altruism_probs: list[float],
		tau_margins: list[float] = None,
		epsilon_fresh_values: list[float] = None,
		epsilon_mono_values: list[float] = None,
		num_simulations: int = 100,
		base_players: dict[str, int] = None,
		base_seed: int = 42,
	) -> list[SimulationResult]:
		"""
		Run a parameter sweep across different configurations.

		Args:
			altruism_probs: List of altruism probabilities to test
			tau_margins: List of tau margin values (default: [0.05])
			epsilon_fresh_values: List of epsilon fresh values (default: [0.05])
			epsilon_mono_values: List of epsilon mono values (default: [0.05])
			num_simulations: Number of simulations per configuration
			base_players: Base player configuration
			base_seed: Base seed for random number generation

		Returns:
			List of all simulation results
		"""
		if tau_margins is None:
			tau_margins = [0.05]
		if epsilon_fresh_values is None:
			epsilon_fresh_values = [0.05]
		if epsilon_mono_values is None:
			epsilon_mono_values = [0.05]
		if base_players is None:
			base_players = {'p10': 1, 'p0': 1, 'p1': 1, 'p2': 1}

		all_results = []
		total_configs = (
			len(altruism_probs)
			* len(tau_margins)
			* len(epsilon_fresh_values)
			* len(epsilon_mono_values)
		)
		total_sims = total_configs * num_simulations

		print(f'Running {total_sims} simulations across {total_configs} configurations...')

		sim_count = 0
		for altruism_prob in altruism_probs:
			for tau_margin in tau_margins:
				for epsilon_fresh in epsilon_fresh_values:
					for epsilon_mono in epsilon_mono_values:
						config = SimulationConfig(
							altruism_prob=altruism_prob,
							tau_margin=tau_margin,
							epsilon_fresh=epsilon_fresh,
							epsilon_mono=epsilon_mono,
							seed=base_seed,
							players=base_players.copy(),
						)

						print(
							f'Testing config: altruism={altruism_prob}, tau={tau_margin}, '
							f'fresh={epsilon_fresh}, mono={epsilon_mono}'
						)

						for _ in range(num_simulations):
							config.seed = base_seed + sim_count
							result = self.run_single_simulation(config)
							all_results.append(result)
							sim_count += 1

							if sim_count % 10 == 0:
								print(f'Completed {sim_count}/{total_sims} simulations')

		self.results = all_results
		return all_results

	def analyze_results(self) -> dict[str, Any]:
		"""
		Analyze the simulation results and return summary statistics.

		Returns:
			Dictionary containing analysis results
		"""
		if not self.results:
			return {}

		# Group results by configuration
		config_groups = defaultdict(list)
		for result in self.results:
			key = (
				result.config.altruism_prob,
				result.config.tau_margin,
				result.config.epsilon_fresh,
				result.config.epsilon_mono,
			)
			config_groups[key].append(result)

		analysis = {
			'total_simulations': len(self.results),
			'unique_configurations': len(config_groups),
			'config_summaries': {},
			'best_configurations': [],
		}

		# Analyze each configuration
		config_scores = []
		for config_key, results in config_groups.items():
			scores = [r.total_score for r in results]
<<<<<<< HEAD
			player10_totals = [
				r.player10_total_mean for r in results if r.player10_total_mean is not None
			]
			player10_individuals = [
				r.player10_individual_mean
				for r in results
				if r.player10_individual_mean is not None
			]
			player10_ranks = [
				r.player10_rank_mean for r in results if r.player10_rank_mean is not None
			]
			player10_gaps = [
				r.player10_gap_to_best for r in results if r.player10_gap_to_best is not None
			]
			best_totals = [r.best_total_score for r in results]

			score_components: dict[str, list[float]] = defaultdict(list)
			for result in results:
				for component, value in result.score_breakdown.items():
					if component == 'total':
						continue
					score_components[component].append(value)

			def _stat(values: list[float]) -> dict[str, float]:
				if not values:
					return {'mean': 0.0, 'std': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0}
				return {
					'mean': sum(values) / len(values),
					'std': self._calculate_std(values),
					'min': min(values),
					'max': max(values),
					'count': len(values),
				}
=======
			player10_scores = [r.player_scores.get('Player10', 0) for r in results]
>>>>>>> lsig/main

			summary = {
				'config': {
					'altruism_prob': config_key[0],
					'tau_margin': config_key[1],
					'epsilon_fresh': config_key[2],
					'epsilon_mono': config_key[3],
				},
				'total_score': {
					'mean': sum(scores) / len(scores),
					'std': self._calculate_std(scores),
					'min': min(scores),
					'max': max(scores),
<<<<<<< HEAD
					'count': len(scores),
				},
				'player10_score': _stat(player10_totals),
				'player10_individual': _stat(player10_individuals),
				'player10_rank': _stat(player10_ranks),
				'player10_gap_to_best': _stat(player10_gaps),
				'best_total_score': _stat(best_totals),
=======
				},
				'player10_score': {
					'mean': sum(player10_scores) / len(player10_scores),
					'std': self._calculate_std(player10_scores),
					'min': min(player10_scores),
					'max': max(player10_scores),
				},
>>>>>>> lsig/main
				'conversation_metrics': {
					'avg_length': sum(r.conversation_length for r in results) / len(results),
					'early_termination_rate': sum(r.early_termination for r in results)
					/ len(results),
					'avg_pause_count': sum(r.pause_count for r in results) / len(results),
					'avg_unique_items': sum(r.unique_items_used for r in results) / len(results),
				},
<<<<<<< HEAD
				'score_components': {
					component: _stat(values) for component, values in score_components.items()
				},
=======
>>>>>>> lsig/main
			}

			analysis['config_summaries'][str(config_key)] = summary
			config_scores.append((config_key, summary['total_score']['mean']))

		# Find best configurations
		config_scores.sort(key=lambda x: x[1], reverse=True)
		analysis['best_configurations'] = [
			{'config': config_key, 'mean_score': score} for config_key, score in config_scores[:5]
		]

		return analysis

<<<<<<< HEAD
	def save_results(self, filename: str = None, metadata: dict[str, Any] | None = None) -> str:
=======
	def save_results(self, filename: str = None) -> str:
>>>>>>> lsig/main
		"""
		Save simulation results to a JSON file.

		Args:
			filename: Optional filename (default: timestamp-based)

		Returns:
			Path to the saved file
		"""
		if filename is None:
			timestamp = int(time.time())
			filename = f'simulation_results_{timestamp}.json'

		filepath = self.output_dir / filename

		# Convert results to serializable format
		serializable_results = []
		for result in self.results:
			serializable_results.append(
				{
					'config': asdict(result.config),
					'total_score': result.total_score,
					'player_scores': result.player_scores,
					'player_contributions': result.player_contributions,
					'conversation_length': result.conversation_length,
					'early_termination': result.early_termination,
					'pause_count': result.pause_count,
					'unique_items_used': result.unique_items_used,
					'execution_time': result.execution_time,
<<<<<<< HEAD
					'score_breakdown': result.score_breakdown,
					'player_metrics': result.player_metrics,
					'player10_total_mean': result.player10_total_mean,
					'player10_individual_mean': result.player10_individual_mean,
					'player10_rank_mean': result.player10_rank_mean,
					'player10_instances': result.player10_instances,
					'best_total_score': result.best_total_score,
					'player10_gap_to_best': result.player10_gap_to_best,
				}
			)

		payload = {
			'metadata': metadata or {},
			'results': serializable_results,
		}
		self.last_metadata = payload['metadata']

		with open(filepath, 'w') as f:
			json.dump(payload, f, indent=2)
=======
				}
			)

		with open(filepath, 'w') as f:
			json.dump(serializable_results, f, indent=2)
>>>>>>> lsig/main

		print(f'Results saved to: {filepath}')
		return str(filepath)

	def load_results(self, filename: str) -> list[SimulationResult]:
		"""
		Load simulation results from a JSON file.

		Args:
			filename: Name of the file to load

		Returns:
			List of simulation results
		"""
		# Support absolute paths or already-qualified paths
		candidate = Path(filename)
		if candidate.is_absolute() or candidate.exists():
			filepath = candidate
		else:
			filepath = self.output_dir / filename

		with open(filepath) as f:
			data = json.load(f)

<<<<<<< HEAD
		if isinstance(data, dict) and 'results' in data:
			raw_results = data['results']
			self.last_metadata = data.get('metadata', {})
		else:
			raw_results = data
			self.last_metadata = {}

		results = []
		for item in raw_results:
=======
		results = []
		for item in data:
>>>>>>> lsig/main
			config = SimulationConfig(**item['config'])
			result = SimulationResult(
				config=config,
				total_score=item['total_score'],
				player_scores=item['player_scores'],
				player_contributions=item['player_contributions'],
				conversation_length=item['conversation_length'],
				early_termination=item['early_termination'],
				pause_count=item['pause_count'],
				unique_items_used=item['unique_items_used'],
				execution_time=item['execution_time'],
<<<<<<< HEAD
				score_breakdown=item.get('score_breakdown', {}),
				player_metrics=item.get('player_metrics', {}),
				player10_total_mean=item.get('player10_total_mean'),
				player10_individual_mean=item.get('player10_individual_mean'),
				player10_rank_mean=item.get('player10_rank_mean'),
				player10_instances=item.get('player10_instances', 0),
				best_total_score=item.get('best_total_score', 0.0),
				player10_gap_to_best=item.get('player10_gap_to_best'),
=======
>>>>>>> lsig/main
			)
			results.append(result)

		self.results = results
		return results

<<<<<<< HEAD
	def _create_players(
		self, player_config: dict[str, int]
	) -> tuple[list[type[Player]], list[dict[str, str]]]:
		"""Resolve player classes from config entries and record metadata."""
		players: list[type[Player]] = []
		metadata: list[dict[str, str]] = []
		resolved: dict[str, type[Player]] = {}

		for player_type, count in player_config.items():
			if count <= 0:
				continue

			if player_type not in resolved:
				resolved[player_type] = self._resolve_player_class(player_type)

			player_cls = resolved[player_type]
			for _ in range(count):
				players.append(player_cls)
				metadata.append(
					{
						'alias': player_type,
						'class_name': player_cls.__name__,
						'module': player_cls.__module__,
					}
				)

		return players, metadata

	@staticmethod
	def _resolve_player_class(player_type: str) -> type[Player]:
		"""Dynamically import the requested player class."""
		alias_map = {
			'pr': ('players.random_player', 'RandomPlayer'),
			'pause': ('players.pause_player', 'PausePlayer'),
			'random_pause': ('players.random_pause_player', 'RandomPausePlayer'),
			'p10': ('players.player_10.agent.player', 'Player10'),
		}

		if player_type in alias_map:
			module_path, class_name = alias_map[player_type]
		elif player_type.startswith('p') and player_type[1:].isdigit():
			module_path = f'players.player_{player_type[1:]}.player'
			class_name = f'Player{int(player_type[1:])}'
		else:
			raise ValueError(f"Unknown player type '{player_type}' in configuration.")

		try:
			module = import_module(module_path)
		except ModuleNotFoundError as exc:
			raise ValueError(
				f"Module '{module_path}' not found for player type '{player_type}'."
			) from exc

		try:
			player_cls = getattr(module, class_name)
		except AttributeError as exc:
			raise ValueError(
				f"Player class '{class_name}' not found in module '{module_path}'."
			) from exc

		if not issubclass(player_cls, Player):
			raise TypeError(
				f"Resolved class '{class_name}' for '{player_type}' is not a Player subtype."
			)

		return player_cls
=======
	def _create_players(self, player_config: dict[str, int]) -> list[type[Player]]:
		"""Create player instances based on configuration."""
		from players.player_0.player import Player0
		from players.player_1.player import Player1
		from players.player_2.player import Player2
		from players.random_player import RandomPlayer

		players = []
		player_classes = {
			'p0': Player0,
			'p1': Player1,
			'p2': Player2,
			'p10': Player10,
			'pr': RandomPlayer,
		}

		for player_type, count in player_config.items():
			if player_type in player_classes:
				players.extend([player_classes[player_type]] * count)

		return players
>>>>>>> lsig/main

	def _update_player10_config(self, config: SimulationConfig):
		"""Temporarily update Player10 configuration."""
		import players.player_10.agent.config as config_module

		config_module.ALTRUISM_USE_PROB = config.altruism_prob
		config_module.TAU_MARGIN = config.tau_margin
		config_module.EPSILON_FRESH = config.epsilon_fresh
		config_module.EPSILON_MONO = config.epsilon_mono
		config_module.MIN_SAMPLES_PID = config.min_samples_pid
		config_module.EWMA_ALPHA = config.ewma_alpha
		config_module.IMPORTANCE_WEIGHT = config.importance_weight
		config_module.COHERENCE_WEIGHT = config.coherence_weight
		config_module.FRESHNESS_WEIGHT = config.freshness_weight
		config_module.MONOTONY_WEIGHT = config.monotony_weight

	def _reset_player10_config(self):
		"""Reset Player10 configuration to original values."""
		# Note: we do not have original snapshot; leave as-is after run to avoid conflicting concurrent tests.
		# For isolation, each run sets values explicitly before it starts.

	def _extract_results(
<<<<<<< HEAD
		self,
		config: SimulationConfig,
		simulation_results: Any,
		execution_time: float,
		player_meta: list[dict[str, str]],
=======
		self, config: SimulationConfig, simulation_results: Any, execution_time: float
>>>>>>> lsig/main
	) -> SimulationResult:
		"""Extract results from engine simulation output."""
		# Extract data from simulation results dictionary
		history = simulation_results.get('history', [])
		score_breakdown = simulation_results.get('score_breakdown', {})
		scores = simulation_results.get('scores', {})
<<<<<<< HEAD
		raw_player_scores = scores.get('player_scores', [])

		# Total shared score comes directly from the breakdown
		total_score = score_breakdown.get('total', 0.0)

		# Prepare per-player metrics
		player_metrics: dict[str, dict[str, Any]] = {}
		player_scores: dict[str, float] = {}
		id_to_label: dict[str, str] = {}
		label_counts: dict[str, int] = defaultdict(int)

		player10_totals: list[float] = []
		player10_individuals: list[float] = []
		player10_ranks: list[float] = []
		player10_gaps: list[float] = []

		# First pass: gather totals for ranking
		player_entries: list[dict[str, Any]] = []
		for idx, player_data in enumerate(raw_player_scores):
			score_data = player_data.get('scores', {})
			total = float(score_data.get('total', 0.0))
			individual = float(score_data.get('individual', 0.0))
			shared = float(score_data.get('shared', total_score))
			player_id = str(player_data.get('id'))

			meta = player_meta[idx] if idx < len(player_meta) else {}
			class_name = meta.get('class_name', 'UnknownPlayer')
			alias = meta.get('alias', class_name.lower())

			player_entries.append(
				{
					'id': player_id,
					'class_name': class_name,
					'alias': alias,
					'total': total,
					'individual': individual,
					'shared': shared,
				}
			)

		# Compute rankings (1 = best). Use strict comparison to preserve ties.
		totals = [entry['total'] for entry in player_entries]
		best_total = max(totals) if totals else 0.0
		for entry in player_entries:
			rank = 1 + sum(1 for value in totals if value > entry['total'])
			entry['rank'] = rank

		# Build labeled metrics and aggregate Player10 stats
		for entry in player_entries:
			base_label = entry['class_name']
			label_counts[base_label] += 1
			label = (
				base_label
				if label_counts[base_label] == 1
				else f'{base_label}#{label_counts[base_label]}'
			)

			id_to_label[entry['id']] = label

			player_metrics[label] = {
				'class_name': entry['class_name'],
				'alias': entry['alias'],
				'total': entry['total'],
				'individual': entry['individual'],
				'shared': entry['shared'],
				'rank': entry['rank'],
			}
			player_scores[label] = entry['total']

			if entry['class_name'] == 'Player10':
				player10_totals.append(entry['total'])
				player10_individuals.append(entry['individual'])
				player10_ranks.append(entry['rank'])
				player10_gaps.append(best_total - entry['total'])

		# Calculate player contributions
		player_contribution_counts: dict[str, int] = defaultdict(int)
		for item in history:
			if item is not None and hasattr(item, 'player_id'):
				player_id = str(item.player_id)
				label = id_to_label.get(player_id)
				if label is None:
					label = f'Player_{player_id[:8]}'
				player_contribution_counts[label] += 1

		player_contributions = {
			label: player_contribution_counts.get(label, 0) for label in player_metrics
		}

		# Legacy convenience entry for Player10 mean total score (if present)
		if player10_totals:
			player_scores['Player10'] = sum(player10_totals) / len(player10_totals)

		player10_total_mean = (
			sum(player10_totals) / len(player10_totals) if player10_totals else None
		)
		player10_individual_mean = (
			sum(player10_individuals) / len(player10_individuals) if player10_individuals else None
		)
		player10_rank_mean = sum(player10_ranks) / len(player10_ranks) if player10_ranks else None
		player10_gap_mean = sum(player10_gaps) / len(player10_gaps) if player10_gaps else None
=======

		# Calculate total score from score breakdown
		total_score = sum(score_breakdown.values()) if score_breakdown else 0.0

		# Calculate player scores (individual contributions)
		player_scores = {}
		# For now, use a simple approach - we'll improve this later
		if 'individual_scores' in scores:
			for player_id_str, score in scores['individual_scores'].items():
				player_scores[f'Player_{player_id_str[:8]}'] = score
		else:
			# Fallback: distribute total score equally among players
			num_players = len(
				[item for item in history if item is not None and hasattr(item, 'player_id')]
			)
			if num_players > 0:
				avg_score = total_score / num_players
				player_scores['Player10'] = avg_score

		# Calculate player contributions
		player_contributions = {}
		# Count contributions by player
		player_contribution_counts = {}
		for item in history:
			if item is not None and hasattr(item, 'player_id'):
				player_id = str(item.player_id)
				player_contribution_counts[player_id] = (
					player_contribution_counts.get(player_id, 0) + 1
				)

		for player_id, count in player_contribution_counts.items():
			player_contributions[f'Player_{player_id[:8]}'] = count
>>>>>>> lsig/main

		# Calculate conversation metrics
		conversation_length = len(history)
		pause_count = sum(1 for item in history if item is None)
		early_termination = conversation_length < config.conversation_length

		# Count unique items used
		unique_items = set()
		for item in history:
			if item is not None:
				unique_items.add(item.id)

		return SimulationResult(
			config=config,
			total_score=total_score,
			player_scores=player_scores,
			player_contributions=player_contributions,
			conversation_length=conversation_length,
			early_termination=early_termination,
			pause_count=pause_count,
			unique_items_used=len(unique_items),
			execution_time=execution_time,
<<<<<<< HEAD
			score_breakdown=score_breakdown,
			player_metrics=player_metrics,
			player10_total_mean=player10_total_mean,
			player10_individual_mean=player10_individual_mean,
			player10_rank_mean=player10_rank_mean,
			player10_instances=len(player10_totals),
			best_total_score=best_total,
			player10_gap_to_best=player10_gap_mean,
=======
>>>>>>> lsig/main
		)

	def _calculate_std(self, values: list[float]) -> float:
		"""Calculate standard deviation."""
		if len(values) < 2:
			return 0.0

		mean = sum(values) / len(values)
		variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
		return variance**0.5


def run_altruism_sweep():
	"""Run a parameter sweep testing different altruism probabilities."""
	simulator = MonteCarloSimulator()

	# Test different altruism probabilities
	altruism_probs = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

	print('Starting altruism probability sweep...')
	simulator.run_parameter_sweep(
		altruism_probs=altruism_probs,
		num_simulations=50,
		base_players={'p10': 1, 'p0': 1, 'p1': 1, 'p2': 1},
	)

	# Analyze results
	analysis = simulator.analyze_results()

	# Print summary
	print('\n=== SIMULATION RESULTS ===')
	print(f'Total simulations: {analysis["total_simulations"]}')
	print(f'Unique configurations: {analysis["unique_configurations"]}')

	print('\n=== TOP 5 CONFIGURATIONS ===')
	for i, config in enumerate(analysis['best_configurations'], 1):
		print(f'{i}. Altruism: {config["config"][0]:.1f}, Mean Score: {config["mean_score"]:.2f}')

	# Save results
	filename = simulator.save_results()
	print(f'\nResults saved to: {filename}')

	return simulator, analysis


if __name__ == '__main__':
	run_altruism_sweep()
