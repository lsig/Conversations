"""
Flexible test configuration framework for Player10 Monte Carlo simulations.

This module provides a flexible way to define and run custom test configurations
without being limited to predefined test types.
"""

import re
import sys
import time
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .monte_carlo import MonteCarloSimulator, SimulationConfig, SimulationResult
from .parallel import execute_in_parallel
from ..agent.config import (
	ALTRUISM_USE_PROB,
	TAU_MARGIN,
	EPSILON_FRESH,
	EPSILON_MONO,
	MIN_SAMPLES_PID,
	EWMA_ALPHA,
	IMPORTANCE_WEIGHT,
	COHERENCE_WEIGHT,
	FRESHNESS_WEIGHT,
	MONOTONY_WEIGHT,
)

# Try to import tqdm once at module load and force-enable it when available
try:
	from tqdm import tqdm  # type: ignore
except Exception:  # pragma: no cover
	tqdm = None  # type: ignore


@dataclass
class ParameterRange:
	"""Defines a range of values for a parameter."""

	values: list[Any]
	name: str
	description: str = ''


@dataclass
class TestConfiguration:
	"""Configuration for a custom test."""

	name: str
	description: str = ''

	# Parameter ranges to test
	altruism_probs: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[ALTRUISM_USE_PROB],
			name='altruism_prob',
			description='Altruism probability',
		)
	)
	tau_margins: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[TAU_MARGIN], name='tau_margin', description='Tau margin'
		)
	)
	epsilon_fresh_values: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[EPSILON_FRESH], name='epsilon_fresh', description='Epsilon fresh'
		)
	)
	epsilon_mono_values: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[EPSILON_MONO], name='epsilon_mono', description='Epsilon mono'
		)
	)

	# Player configurations to test
	player_configs: list[dict[str, int]] = field(default_factory=lambda: [{'p10': 10}])

	# Simulation parameters
	num_simulations: int = 50
	conversation_length: int = 50
	subjects: int = 20
	memory_size: int = 10
	base_seed: int = 42

	# Output settings
	output_dir: str = 'players/player_10/results'
	save_results: bool = True
	print_progress: bool = True
	# Parallel execution controls
	parallel: bool = False
	workers: int | None = None
	# Extended knobs (optional ranges)
	min_samples_values: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[MIN_SAMPLES_PID],
			name='min_samples_pid',
			description='Min samples per player for trusted mean',
		)
	)
	ewma_alpha_values: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[EWMA_ALPHA], name='ewma_alpha', description='EWMA alpha'
		)
	)
	importance_weights: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[IMPORTANCE_WEIGHT], name='importance_weight', description='Importance weight'
		)
	)
	coherence_weights: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[COHERENCE_WEIGHT], name='coherence_weight', description='Coherence weight'
		)
	)
	freshness_weights: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[FRESHNESS_WEIGHT], name='freshness_weight', description='Freshness weight'
		)
	)
	monotony_weights: ParameterRange = field(
		default_factory=lambda: ParameterRange(
			values=[MONOTONY_WEIGHT], name='monotony_weight', description='Monotony weight'
		)
	)


class TestBuilder:
	"""Builder class for creating custom test configurations."""

	def __init__(self, name: str, description: str = ''):
		self.config = TestConfiguration(name=name, description=description)

	def altruism_range(self, values: list[float]) -> 'TestBuilder':
		"""Set altruism probability range."""
		self.config.altruism_probs = ParameterRange(
			values=values, name='altruism_prob', description='Altruism probability'
		)
		return self

	def tau_range(self, values: list[float]) -> 'TestBuilder':
		"""Set tau margin range."""
		self.config.tau_margins = ParameterRange(
			values=values, name='tau_margin', description='Tau margin'
		)
		return self

	def epsilon_fresh_range(self, values: list[float]) -> 'TestBuilder':
		"""Set epsilon fresh range."""
		self.config.epsilon_fresh_values = ParameterRange(
			values=values, name='epsilon_fresh', description='Epsilon fresh'
		)
		return self

	def epsilon_mono_range(self, values: list[float]) -> 'TestBuilder':
		"""Set epsilon mono range."""
		self.config.epsilon_mono_values = ParameterRange(
			values=values, name='epsilon_mono', description='Epsilon mono'
		)
		return self

	def player_configs(self, configs: list[dict[str, int]]) -> 'TestBuilder':
		"""Set player configurations to test."""
		self.config.player_configs = configs
		return self

	def add_player_config(self, config: dict[str, int]) -> 'TestBuilder':
		"""Add a player configuration."""
		self.config.player_configs.append(config)
		return self

	def simulations(self, count: int) -> 'TestBuilder':
		"""Set number of simulations per configuration."""
		self.config.num_simulations = count
		return self

	def conversation_length(self, length: int) -> 'TestBuilder':
		"""Set conversation length."""
		self.config.conversation_length = length
		return self

	def subjects(self, count: int) -> 'TestBuilder':
		"""Set number of subjects."""
		self.config.subjects = count
		return self

	def memory_size(self, size: int) -> 'TestBuilder':
		"""Set memory size."""
		self.config.memory_size = size
		return self

	# Extended range setters
	def min_samples_range(self, values: list[int]) -> 'TestBuilder':
		self.config.min_samples_values = ParameterRange(
			values=values, name='min_samples_pid', description='Min samples per player'
		)
		return self

	def ewma_alpha_range(self, values: list[float]) -> 'TestBuilder':
		self.config.ewma_alpha_values = ParameterRange(
			values=values, name='ewma_alpha', description='EWMA alpha'
		)
		return self

	def importance_weight_range(self, values: list[float]) -> 'TestBuilder':
		self.config.importance_weights = ParameterRange(
			values=values, name='importance_weight', description='Importance weight'
		)
		return self

	def coherence_weight_range(self, values: list[float]) -> 'TestBuilder':
		self.config.coherence_weights = ParameterRange(
			values=values, name='coherence_weight', description='Coherence weight'
		)
		return self

	def freshness_weight_range(self, values: list[float]) -> 'TestBuilder':
		self.config.freshness_weights = ParameterRange(
			values=values, name='freshness_weight', description='Freshness weight'
		)
		return self

	def monotony_weight_range(self, values: list[float]) -> 'TestBuilder':
		self.config.monotony_weights = ParameterRange(
			values=values, name='monotony_weight', description='Monotony weight'
		)
		return self

	def output_dir(self, directory: str) -> 'TestBuilder':
		"""Set output directory."""
		self.config.output_dir = directory
		return self

	def parallel(self, enabled: bool, workers: int | None = None) -> 'TestBuilder':
		"""Enable/disable parallel execution and optionally set workers."""
		self.config.parallel = enabled
		self.config.workers = workers
		return self

	def build(self) -> TestConfiguration:
		"""Build the test configuration."""
		return self.config


class FlexibleTestRunner:
	"""Flexible test runner that can execute any test configuration."""

	def __init__(self, output_dir: str = 'players/player_10/results'):
		self.output_dir = Path(output_dir)
		self.output_dir.mkdir(exist_ok=True)
		self.simulator = MonteCarloSimulator(str(self.output_dir))
		self.results: list[SimulationResult] = []

	def _build_task_args(
		self, sim_config: SimulationConfig, config: TestConfiguration, combination_count: int
	) -> list[tuple[SimulationConfig, str]]:
		tasks: list[tuple[SimulationConfig, str]] = []
		for sim_idx in range(config.num_simulations):
			run_cfg = SimulationConfig(
				altruism_prob=sim_config.altruism_prob,
				tau_margin=sim_config.tau_margin,
				epsilon_fresh=sim_config.epsilon_fresh,
				epsilon_mono=sim_config.epsilon_mono,
				seed=config.base_seed + combination_count * config.num_simulations + sim_idx,
				players=sim_config.players,
				subjects=sim_config.subjects,
				memory_size=sim_config.memory_size,
				conversation_length=sim_config.conversation_length,
				min_samples_pid=sim_config.min_samples_pid,
				ewma_alpha=sim_config.ewma_alpha,
				importance_weight=sim_config.importance_weight,
				coherence_weight=sim_config.coherence_weight,
				freshness_weight=sim_config.freshness_weight,
				monotony_weight=sim_config.monotony_weight,
			)
			tasks.append((run_cfg, str(self.output_dir)))
		return tasks

	def run_test(self, config: TestConfiguration) -> list[SimulationResult]:
		"""
		Run a test configuration.

		Args:
			config: Test configuration to run

		Returns:
			List of simulation results
		"""
		print(f'=== RUNNING TEST: {config.name} ===')
		if config.description:
			print(f'Description: {config.description}')

		combination_total = self._count_combinations(config)
		total_simulations = combination_total * config.num_simulations
		run_started = datetime.now()

		print(f'Parameter combinations: {combination_total}')
		print(f'Total simulations: {total_simulations}')
		print()

		all_results = []
		combination_count = 0
		total_combinations = combination_total
		pbar = None
		if config.print_progress and total_simulations > 0:
			if tqdm is not None:
				try:
					pbar = tqdm(
						total=total_simulations,
						desc='Simulations',
						leave=True,
						dynamic_ncols=True,
						miniters=1,
						smoothing=0.1,
						file=sys.stdout,
						disable=False,
					)
				except Exception:
					pbar = None
			else:
				pbar = None

		# Generate all parameter combinations
		for param_combo in self._generate_parameter_combinations(config):
			for player_config in config.player_configs:
				combination_count += 1

				if config.print_progress:
					# Keep progress bar as the main output; no extra lines
						a = param_combo['altruism_prob']
						t = param_combo['tau_margin']
						ef = param_combo['epsilon_fresh']
						em = param_combo['epsilon_mono']
						postfix = (
							f'combo {combination_count}/{total_combinations} '
							f'a={a:.2f},τ={t:.2f},εf={ef:.2f},εm={em:.2f} players={player_config}'
						)
						if pbar is not None:
							try:
								pbar.set_description('Simulations')
								pbar.set_postfix_str(postfix)
							except Exception:
								pass
						else:
							# Minimal inline fallback without creating new lines
							sys.stdout.write('\r' + postfix + ' ' * 10)
							sys.stdout.flush()

				sim_config = SimulationConfig(
					altruism_prob=param_combo['altruism_prob'],
					tau_margin=param_combo['tau_margin'],
					epsilon_fresh=param_combo['epsilon_fresh'],
					epsilon_mono=param_combo['epsilon_mono'],
					seed=config.base_seed + combination_count,
					players=player_config,
					subjects=config.subjects,
					memory_size=config.memory_size,
					conversation_length=config.conversation_length,
					min_samples_pid=param_combo.get(
						'min_samples_pid', config.min_samples_values.values[0]
					),
					ewma_alpha=param_combo.get('ewma_alpha', config.ewma_alpha_values.values[0]),
					importance_weight=param_combo.get(
						'importance_weight', config.importance_weights.values[0]
					),
					coherence_weight=param_combo.get(
						'coherence_weight', config.coherence_weights.values[0]
					),
					freshness_weight=param_combo.get(
						'freshness_weight', config.freshness_weights.values[0]
					),
					monotony_weight=param_combo.get(
						'monotony_weight', config.monotony_weights.values[0]
					),
				)

				if config.parallel:
					task_args = self._build_task_args(sim_config, config, combination_count)
					for result in execute_in_parallel(task_args, workers=config.workers):
						all_results.append(result)
						if pbar is not None:
							pbar.update(1)
				else:
					for sim_idx in range(config.num_simulations):
						sim_config.seed = (
							config.base_seed + combination_count * config.num_simulations + sim_idx
						)
						result = self.simulator.run_single_simulation(sim_config)
						all_results.append(result)
						if pbar is not None:
							pbar.update(1)

		if pbar is not None:
			pbar.close()

		self.results = all_results

		if config.save_results:
			timestamp_label = run_started.strftime('%Y%m%d_%H%M%S')
			name_slug = self._slugify_name(config.name)
			filename = f'{timestamp_label}_{name_slug}.json'
			metadata = self._build_metadata(
				config=config,
				filename=filename,
				run_started=run_started,
				total_combinations=total_combinations,
				total_simulations=total_simulations,
			)
			self.simulator.results = all_results
			self.simulator.save_results(filename, metadata=metadata)

		print(f'Test completed: {len(all_results)} simulations')
		return all_results

	def run_multiple_tests(
		self, configs: list[TestConfiguration]
	) -> dict[str, list[SimulationResult]]:
		"""
		Run multiple test configurations.

		Args:
			configs: List of test configurations

		Returns:
			Dictionary mapping test names to results
		"""
		all_results = {}

		for config in configs:
			results = self.run_test(config)
			all_results[config.name] = results
			print()

		return all_results

	def _count_combinations(self, config: TestConfiguration) -> int:
		"""Count total parameter combinations across all ranges and player configs."""
		param_count = (
			len(config.altruism_probs.values)
			* len(config.tau_margins.values)
			* len(config.epsilon_fresh_values.values)
			* len(config.epsilon_mono_values.values)
			* len(config.min_samples_values.values)
			* len(config.ewma_alpha_values.values)
			* len(config.importance_weights.values)
			* len(config.coherence_weights.values)
			* len(config.freshness_weights.values)
			* len(config.monotony_weights.values)
		)
		return param_count * len(config.player_configs)

	def _generate_parameter_combinations(self, config: TestConfiguration) -> list[dict[str, Any]]:
		"""Generate all parameter combinations."""
		combinations = []

		for altruism in config.altruism_probs.values:
			for tau in config.tau_margins.values:
				for fresh in config.epsilon_fresh_values.values:
					for mono in config.epsilon_mono_values.values:
						for min_samples in config.min_samples_values.values:
							for ewma in config.ewma_alpha_values.values:
								for w_imp in config.importance_weights.values:
									for w_coh in config.coherence_weights.values:
										for w_fre in config.freshness_weights.values:
											for w_mon in config.monotony_weights.values:
												combinations.append(
													{
														'altruism_prob': altruism,
														'tau_margin': tau,
														'epsilon_fresh': fresh,
														'epsilon_mono': mono,
														'min_samples_pid': min_samples,
														'ewma_alpha': ewma,
														'importance_weight': w_imp,
														'coherence_weight': w_coh,
														'freshness_weight': w_fre,
														'monotony_weight': w_mon,
													}
												)

		return combinations

	@staticmethod
	def _slugify_name(name: str | None) -> str:
		value = (name or 'run').strip().lower()
		value = re.sub(r'[^a-z0-9_-]+', '-', value)
		value = value.strip('-')
		return value or 'run'

	def _build_metadata(
		self,
		config: TestConfiguration,
		filename: str,
		run_started: datetime,
		total_combinations: int,
		total_simulations: int,
	) -> dict[str, Any]:
		"""Create a metadata summary describing this run."""
		return {
			'run_name': config.name,
			'description': config.description,
			'generated_at': run_started.isoformat(),
			'output_dir': str(self.output_dir),
			'filename': filename,
			'cli_command': ' '.join(sys.argv),
			'base_seed': config.base_seed,
			'parallel': config.parallel,
			'workers': config.workers,
			'parameter_combinations': total_combinations,
			'simulations_per_configuration': config.num_simulations,
			'total_simulations': total_simulations,
			'player_configs': config.player_configs,
			'conversation_length': config.conversation_length,
			'subjects': config.subjects,
			'memory_size': config.memory_size,
			'ranges': {
				'altruism_prob': list(config.altruism_probs.values),
				'tau_margin': list(config.tau_margins.values),
				'epsilon_fresh': list(config.epsilon_fresh_values.values),
				'epsilon_mono': list(config.epsilon_mono_values.values),
				'min_samples_pid': list(config.min_samples_values.values),
				'ewma_alpha': list(config.ewma_alpha_values.values),
				'importance_weight': list(config.importance_weights.values),
				'coherence_weight': list(config.coherence_weights.values),
				'freshness_weight': list(config.freshness_weights.values),
				'monotony_weight': list(config.monotony_weights.values),
			},
			'flags': {
				'save_results': config.save_results,
				'print_progress': config.print_progress,
			},
		}


# Predefined test configurations for common use cases
def create_altruism_comparison_test() -> TestConfiguration:
	"""Create a test comparing different altruism probabilities."""
	return (
		TestBuilder('altruism_comparison', 'Compare different altruism probabilities')
		.altruism_range([0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0])
		.player_configs([{'p10': 10}])
		.simulations(50)
		.build()
	)


def create_random_players_test(num_random: int) -> TestConfiguration:
	"""Create a test against random players."""
	return (
		TestBuilder(f'random_{num_random}', f'Test against {num_random} random players')
		.altruism_range([0.0, 0.2, 0.5, 1.0])
		.player_configs([{'p10': 10, 'pr': num_random}])
		.simulations(50)
		.build()
	)


def create_scalability_test() -> TestConfiguration:
	"""Create a scalability test with different numbers of random players."""
	return (
		TestBuilder('scalability', 'Test scalability with different random player counts')
		.altruism_range([0.0, 0.5, 1.0])
		.player_configs([{'p10': 10, 'pr': 2}, {'p10': 10, 'pr': 5}, {'p10': 10, 'pr': 10}])
		.simulations(30)
		.build()
	)


def create_parameter_sweep_test() -> TestConfiguration:
	"""Create a comprehensive parameter sweep test."""
	return (
		TestBuilder('parameter_sweep', 'Comprehensive parameter sweep')
		.altruism_range([0.0, 0.1, 0.15, 0.2, 0.25, 0.3])
		.tau_range([-0.1, 0, 0.05, 0.1, 0.15, 0.2, 0.25])
		.epsilon_fresh_range([-0.05, 0, 0.05, 0.1, 0.15])
		.epsilon_mono_range([-0.05, 0, 0.05, 0.1])
		.player_configs([{'p10': 8, 'pr': 0}])  # , {'p10': 9, 'pr': 1}])
		.simulations(20)
		.build()
	)


def create_mixed_opponents_test() -> TestConfiguration:
	"""Create a test against mixed opponent types."""
	return (
		TestBuilder('mixed_opponents', 'Test against mixed opponent types')
		.altruism_range([0.0, 0.2, 0.5, 1.0])
		.player_configs([{'p10': 10, 'p0': 2, 'p1': 2, 'p2': 2, 'pr': 4}])
		.simulations(50)
		.build()
	)


# Example usage and demo functions
def run_example_tests():
	"""Run example tests to demonstrate the framework."""
	runner = FlexibleTestRunner()

	# Create some example tests
	tests = [
		create_altruism_comparison_test(),
		create_random_players_test(5),
		create_scalability_test(),
	]

	# Run all tests
	results = runner.run_multiple_tests(tests)

	# Print summary
	print('\n=== TEST SUMMARY ===')
	for test_name, test_results in results.items():
		print(f'{test_name}: {len(test_results)} simulations')

	return results


if __name__ == '__main__':
	run_example_tests()
