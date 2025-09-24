"""Player10 Monte Carlo runner CLI.

Provides a single entry point (``python -m players.player_10.tools.run``)
for launching predefined or custom Monte Carlo sweeps from the command line.
"""

import argparse
import json
import re
from pathlib import Path

from ..sim.test_framework import (
	FlexibleTestRunner,
	ParameterRange,
	TestBuilder,
	TestConfiguration,
	create_altruism_comparison_test,
	create_mixed_opponents_test,
	create_parameter_sweep_test,
	create_random_players_test,
	create_scalability_test,
)
from .dashboard import generate_dashboard
from .reporting import (
	difference_lines,
	format_players,
	parameter_label,
	summarize_parameterizations,
)

_DEFAULT_CONFIG = TestConfiguration(name='cli_defaults')


def _std(values: list[float]) -> float:
	"""Small helper for overall statistics."""
	if len(values) < 2:
		return 0.0
	mean = sum(values) / len(values)
	variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
	return variance**0.5


def _format_values(value) -> str:
	"""Return a compact string representation for defaults."""
	if isinstance(value, list | tuple | set):
		return ', '.join(str(v) for v in value)
	return str(value)


class PrettyHelpFormatter(argparse.RawDescriptionHelpFormatter):
	"""Formatter that keeps defaults, respects manual spacing, and aligns columns."""

	def __init__(
		self,
		prog: str,
		*,
		indent_increment: int = 2,
		max_help_position: int = 32,
		width: int | None = None,
	) -> None:
		super().__init__(
			prog,
			indent_increment=indent_increment,
			max_help_position=max_help_position,
			width=width or 100,
		)

	def _split_lines(self, text: str, width: int) -> list[str]:  # noqa: D401 - override
		if text.startswith('|'):
			text = text[1:].rstrip()
			paragraphs = text.split('\n|')
			lines: list[str] = []
			for paragraph in paragraphs:
				lines.extend(super()._split_lines(paragraph, width))
			return lines
		return super()._split_lines(text, width)

	def _format_action(self, action):  # noqa: D401 - override
		formatted = super()._format_action(action)
		lines = formatted.split('\n')
		if not lines:
			return formatted

		lines[0] = f'  {lines[0]}'
		for idx in range(1, len(lines)):
			lines[idx] = f'      {lines[idx]}'

		return '\n'.join(lines)

	def _get_help_string(self, action):  # noqa: D401 - override
		return action.help or ''


def _parse_player_config_string(config_str: str) -> dict:
	"""Parse a player configuration string into a dict.

	Accepts:
	- Strict JSON (e.g., '{"p10": 10, "pr": 2}')
	- JSON-ish without quoted keys (e.g., '{p10: 10, pr: 2}')
	- Key/value pairs (e.g., 'p10=10 pr=2' or 'p10:10,pr:2')
	"""
	s = config_str.strip()
	# 1) Try strict JSON
	try:
		return json.loads(s)
	except Exception:
		pass

	# 2) Try to repair JSON-ish with unquoted keys and single quotes
	try:
		repaired = s
		repaired = repaired.replace("'", '"')
		repaired = re.sub(r'([\{\[,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', repaired)
		return json.loads(repaired)
	except Exception:
		pass

	# 3) Parse as key/value pairs
	pairs = re.split(r'[\s,]+', s)
	out: dict[str, int] = {}
	for token in pairs:
		if not token:
			continue
		if '=' in token:
			k, v = token.split('=', 1)
		elif ':' in token:
			k, v = token.split(':', 1)
		else:
			# Not a recognizable token, skip
			continue
		k = k.strip().strip('"\'')
		v = v.strip().strip('"\'')
		if not k or not v:
			continue
		try:
			out[k] = int(v)
		except ValueError:
			# Ignore non-int values
			continue
	return out


def create_custom_test_from_args(args) -> TestConfiguration:
	"""Create a custom test configuration from command line arguments."""
	name = (args.name or 'custom').strip() or 'custom'
	builder = TestBuilder(name, args.description or '')

	# Set parameter ranges
	if args.altruism:
		builder.altruism_range(args.altruism)
	if args.tau:
		builder.tau_range(args.tau)
	if args.epsilon_fresh:
		builder.epsilon_fresh_range(args.epsilon_fresh)
	if args.epsilon_mono:
		builder.epsilon_mono_range(args.epsilon_mono)

	# Set player configurations
	if args.players:
		player_configs = []
		for player_str in args.players:
			parsed = _parse_player_config_string(player_str)
			if parsed:
				player_configs.append(parsed)
			else:
				print(f"Warning: Invalid player configuration '{player_str}', skipping")
		if player_configs:
			builder.player_configs(player_configs)

	# Set simulation parameters
	if args.simulations:
		builder.simulations(args.simulations)
	if args.conversation_length:
		builder.conversation_length(args.conversation_length)
	if args.subjects:
		builder.subjects(args.subjects)
	if args.memory_size:
		builder.memory_size(args.memory_size)

	# Parallel options
	if args.parallel:
		builder.parallel(True, args.workers)

	# Extended ranges
	if args.min_samples:
		builder.min_samples_range(args.min_samples)
	if args.ewma:
		builder.ewma_alpha_range(args.ewma)
	if args.w_importance:
		builder.importance_weight_range(args.w_importance)
	if args.w_coherence:
		builder.coherence_weight_range(args.w_coherence)
	if args.w_freshness:
		builder.freshness_weight_range(args.w_freshness)
	if args.w_monotony:
		builder.monotony_weight_range(args.w_monotony)

	# Set output directory
	if args.output_dir:
		builder.output_dir(args.output_dir)

	return builder.build()


def main():
	"""Main command-line interface."""
	parser = argparse.ArgumentParser(
		description='Flexible Monte Carlo test runner for Player10',
		formatter_class=PrettyHelpFormatter,
		epilog="""
Examples:
  # Run predefined altruism comparison test
  python -m players.player_10.tools.run --predefined altruism

  # Run custom test with specific parameters
  python -m players.player_10.tools.run --name "my_test" --altruism 0.0 0.5 1.0 --simulations 100

  # Test against different numbers of random players
  python -m players.player_10.tools.run --name "random_test" --players '{"p10": 10, "pr": 5}' --altruism 0.0 0.5 1.0

  # Run multiple player configurations
  python -m players.player_10.tools.run --name "multi_config" --players '{"p10": 10}' '{"p10": 10, "pr": 2}' '{"p10": 10, "pr": 5}'
		""",
	)

	# Run selection
	selection_group = parser.add_mutually_exclusive_group()
	selection_group.add_argument(
		'--predefined',
		choices=[
			'altruism',
			'random2',
			'random5',
			'random10',
			'scalability',
			'parameter_sweep',
			'mixed',
		],
		help='|Run one of the canned sweeps (ignores custom ranges).\n|Default: none.',
	)
	selection_group.add_argument(
		'--name', help='|Label saved outputs; defaults to an auto-generated timestamp.'
	)

	meta_group = parser.add_argument_group('run metadata')
	meta_group.add_argument('--description', help='|Optional note recorded in the metadata block.')

	range_defaults = _DEFAULT_CONFIG
	range_group = parser.add_argument_group('parameter ranges')
	range_group.add_argument(
		'--altruism',
		nargs='+',
		type=float,
		help=f'|Altruism probabilities to evaluate.\n|Default: {_format_values(range_defaults.altruism_probs.values)}',
	)
	range_group.add_argument(
		'--tau',
		nargs='+',
		type=float,
		help=f'|Tau margins for the altruism gate.\n|Default: {_format_values(range_defaults.tau_margins.values)}',
	)
	range_group.add_argument(
		'--epsilon-fresh',
		nargs='+',
		type=float,
		help=f'|Freshness adjustments applied after pauses.\n|Default: {_format_values(range_defaults.epsilon_fresh_values.values)}',
	)
	range_group.add_argument(
		'--epsilon-mono',
		nargs='+',
		type=float,
		help=f'|Monotony adjustments to the altruism gate.\n|Default: {_format_values(range_defaults.epsilon_mono_values.values)}',
	)
	range_group.add_argument(
		'--min-samples',
		nargs='+',
		type=int,
		help=f'|Samples required before trusting per-player averages.\n|Default: {_format_values(range_defaults.min_samples_values.values)}',
	)
	range_group.add_argument(
		'--ewma',
		nargs='+',
		type=float,
		help=f'|EWMA alpha values for performance tracking.\n|Default: {_format_values(range_defaults.ewma_alpha_values.values)}',
	)
	range_group.add_argument(
		'--w-importance',
		nargs='+',
		type=float,
		help=f'|Importance weight multipliers.\n|Default: {_format_values(range_defaults.importance_weights.values)}',
	)
	range_group.add_argument(
		'--w-coherence',
		nargs='+',
		type=float,
		help=f'|Coherence weight multipliers.\n|Default: {_format_values(range_defaults.coherence_weights.values)}',
	)
	range_group.add_argument(
		'--w-freshness',
		nargs='+',
		type=float,
		help=f'|Freshness weight multipliers.\n|Default: {_format_values(range_defaults.freshness_weights.values)}',
	)
	range_group.add_argument(
		'--w-monotony',
		nargs='+',
		type=float,
		help=f'|Monotony weight multipliers.\n|Default: {_format_values(range_defaults.monotony_weights.values)}',
	)

	player_group = parser.add_argument_group('player setup & schedule')
	player_group.add_argument(
		'--players',
		nargs='+',
		help=(
			f'|Player configuration overrides as JSON (e.g., \'{{"p10": 8, "pr": 2}}\').\n'
			f'|Default: {_DEFAULT_CONFIG.player_configs}'
		),
	)
	player_group.add_argument(
		'--simulations',
		type=int,
		help='|Simulations per configuration. Default: 50.',
	)
	player_group.add_argument(
		'--conversation-length',
		type=int,
		help='|Conversation length in turns. Default: 50.',
	)
	player_group.add_argument(
		'--subjects',
		type=int,
		help='|Subject pool size for item generation. Default: 20.',
	)
	player_group.add_argument(
		'--memory-size',
		type=int,
		help='|Memory bank size per player. Default: 10.',
	)

	exec_group = parser.add_argument_group('execution controls')
	exec_group.add_argument(
		'--parallel',
		action='store_true',
		help='|Run configurations across CPU cores.\n|Default: disabled.',
	)
	exec_group.add_argument(
		'--workers',
		type=int,
		help='|Explicit worker count when using --parallel. Default: auto.',
	)
	exec_group.add_argument(
		'--output-dir',
		help=f"|Directory for saved results. Default: '{_DEFAULT_CONFIG.output_dir}'.",
	)
	exec_group.add_argument(
		'--no-save',
		action='store_true',
		help='|Skip writing JSON output (analysis still runs).',
	)
	exec_group.add_argument(
		'--quiet',
		action='store_true',
		help='|Suppress progress indicators for silent runs.',
	)
	exec_group.add_argument(
		'--no-dashboard',
		action='store_true',
		help='|Skip generating the interactive Plotly dashboard (default: enabled).',
	)

	args = parser.parse_args()

	# Create test configuration
	if args.predefined:
		# Use predefined test
		predefined_tests = {
			'altruism': create_altruism_comparison_test(),
			'random2': create_random_players_test(2),
			'random5': create_random_players_test(5),
			'random10': create_random_players_test(10),
			'scalability': create_scalability_test(),
			'parameter_sweep': create_parameter_sweep_test(),
			'mixed': create_mixed_opponents_test(),
		}
		config = predefined_tests[args.predefined]
	else:
		# Create custom test
		config = create_custom_test_from_args(args)

	# Override settings from command line (applies to both predefined and custom)
	# Parameter ranges
	if args.predefined:
		if args.altruism:
			config.altruism_probs = ParameterRange(
				values=args.altruism, name='altruism_prob', description='Altruism probability'
			)
		if args.tau:
			config.tau_margins = ParameterRange(
				values=args.tau, name='tau_margin', description='Tau margin'
			)
		if args.epsilon_fresh:
			config.epsilon_fresh_values = ParameterRange(
				values=args.epsilon_fresh, name='epsilon_fresh', description='Epsilon fresh'
			)
		if args.epsilon_mono:
			config.epsilon_mono_values = ParameterRange(
				values=args.epsilon_mono, name='epsilon_mono', description='Epsilon mono'
			)
		if args.min_samples:
			config.min_samples_values = ParameterRange(
				values=args.min_samples,
				name='min_samples_pid',
				description='Min samples per player for trusted mean',
			)
		if args.ewma:
			config.ewma_alpha_values = ParameterRange(
				values=args.ewma, name='ewma_alpha', description='EWMA alpha'
			)
		if args.w_importance:
			config.importance_weights = ParameterRange(
				values=args.w_importance, name='importance_weight', description='Importance weight'
			)
		if args.w_coherence:
			config.coherence_weights = ParameterRange(
				values=args.w_coherence, name='coherence_weight', description='Coherence weight'
			)
		if args.w_freshness:
			config.freshness_weights = ParameterRange(
				values=args.w_freshness, name='freshness_weight', description='Freshness weight'
			)
		if args.w_monotony:
			config.monotony_weights = ParameterRange(
				values=args.w_monotony, name='monotony_weight', description='Monotony weight'
			)
		# Player configurations
		if args.players:
			player_configs = []
			for player_str in args.players:
				parsed = _parse_player_config_string(player_str)
				if parsed:
					player_configs.append(parsed)
			if player_configs:
				config.player_configs = player_configs
		# Simulation parameters
		if args.simulations:
			config.num_simulations = args.simulations
		if args.conversation_length:
			config.conversation_length = args.conversation_length
		if args.subjects:
			config.subjects = args.subjects
		if args.memory_size:
			config.memory_size = args.memory_size
		# Parallel
		if args.parallel:
			config.parallel = True
			if args.workers:
				config.workers = args.workers
		# Output directory
		if args.output_dir:
			config.output_dir = args.output_dir

	# Generic flags
	if args.no_save:
		config.save_results = False
	if args.quiet:
		config.print_progress = False

	# Create and run test
	runner = FlexibleTestRunner(config.output_dir)
	results = runner.run_test(config)

	# Print summary
	print('\n=== TEST COMPLETED ===')
	print(f'Test: {config.name}')
	print(f'Total simulations: {len(results)}')
	print(f'Configurations tested: {len(results) // config.num_simulations}')

	# Analyze results if we have them
	if results:
		runner.simulator.results = results
		analysis = runner.simulator.analyze_results()

		# Print comprehensive results table
		print('\n=== COMPREHENSIVE RESULTS TABLE ===')
		print(
			f'{"Rank":<4} {"Altruism":<8} {"Tau":<6} {"Fresh":<6} {"Mono":<6} '
			f'{"Total Score":<12} {"P10 Score":<11} {"Std Dev":<8} '
			f'{"P10 Rank":<12} {"Gap→Top":<12} {"Count":<5}'
		)
		print('-' * 110)

		for i, config_result in enumerate(analysis['best_configurations'], 1):
			altruism, tau, fresh, mono = config_result['config']
			total_score = config_result['mean_score']

			# Get additional stats from config_summaries
			config_key = str(config_result['config'])
			if config_key in analysis['config_summaries']:
				summary = analysis['config_summaries'][config_key]
				p10_score = summary['player10_score']['mean']
				std = summary['total_score']['std']
				count = summary['total_score'].get('count', config.num_simulations)
				rank_stats = summary.get('player10_rank', {})
				gap_stats = summary.get('player10_gap_to_best', {})
				rank_mean = rank_stats.get('mean')
				rank_std = rank_stats.get('std', 0.0)
				rank_count = rank_stats.get('count', 0)
				gap_mean = gap_stats.get('mean')
				gap_std = gap_stats.get('std', 0.0)
				gap_count = gap_stats.get('count', 0)
				p10_rank_str = f'{rank_mean:.2f}±{rank_std:.2f}' if rank_count else 'n/a'
				gap_str = f'{gap_mean:.2f}±{gap_std:.2f}' if gap_count else 'n/a'
			else:
				p10_score = 0.0
				std = 0.0
				count = config.num_simulations
				p10_rank_str = 'n/a'
				gap_str = 'n/a'

			print(
				f'{i:<4} {altruism:<8.1f} {tau:<6.2f} {fresh:<6.2f} {mono:<6.2f} '
				f'{total_score:<12.2f} {p10_score:<11.2f} {std:<8.2f} '
				f'{p10_rank_str:<12} {gap_str:<12} {count:<5}'
			)

		# Print detailed configuration table
		print('\n=== DETAILED CONFIGURATION TABLE ===')
		print(
			f'{"Rank":<4} {"Configuration":<25} {"Total Score":<14} {"P10 Score":<13} '
			f'{"P10 Rank":<12} {"Gap→Top":<12} {"Conv Len":<9} {"Pauses":<7} {"Items":<6} {"Early Term":<10}'
		)
		print('-' * 120)

		for i, config_result in enumerate(analysis['best_configurations'], 1):
			altruism, tau, fresh, mono = config_result['config']
			config_key = str(config_result['config'])

			if config_key in analysis['config_summaries']:
				summary = analysis['config_summaries'][config_key]
				config_str = f'Alt={altruism:.1f},τ={tau:.2f},εf={fresh:.2f},εm={mono:.2f}'
				total_score = (
					f'{summary["total_score"]["mean"]:.2f}±{summary["total_score"]["std"]:.2f}'
				)
				p10_score = f'{summary["player10_score"]["mean"]:.2f}±{summary["player10_score"]["std"]:.2f}'
				rank_stats = summary.get('player10_rank', {})
				rank_count = rank_stats.get('count', 0)
				rank_str = (
					f'{rank_stats.get("mean", 0.0):.2f}±{rank_stats.get("std", 0.0):.2f}'
					if rank_count
					else 'n/a'
				)
				gap_stats = summary.get('player10_gap_to_best', {})
				gap_count = gap_stats.get('count', 0)
				gap_detail = (
					f'{gap_stats.get("mean", 0.0):.2f}±{gap_stats.get("std", 0.0):.2f}'
					if gap_count
					else 'n/a'
				)
				conv_len = f'{summary["conversation_metrics"]["avg_length"]:.1f}'
				pauses = f'{summary["conversation_metrics"]["avg_pause_count"]:.1f}'
				items = f'{summary["conversation_metrics"]["avg_unique_items"]:.1f}'
				early_term = f'{summary["conversation_metrics"]["early_termination_rate"]:.2f}'
			else:
				config_str = f'Alt={altruism:.1f},τ={tau:.2f},εf={fresh:.2f},εm={mono:.2f}'
				total_score = f'{config_result["mean_score"]:.2f}±0.00'
				p10_score = '0.00±0.00'
				rank_str = 'n/a'
				gap_detail = 'n/a'
				conv_len = '50.0'
				pauses = '0.0'
				items = '0.0'
				early_term = '0.00'

				print(
					f'{i:<4} {config_str:<25} {total_score:<14} {p10_score:<13} '
					f'{rank_str:<12} {gap_detail:<12} {conv_len:<9} {pauses:<7} {items:<6} {early_term:<10}'
				)

		# Print top 3 detailed analysis
		print('\n=== TOP 3 DETAILED ANALYSIS ===')
		for i, config_result in enumerate(analysis['best_configurations'][:3], 1):
			altruism, tau, fresh, mono = config_result['config']
			config_key = str(config_result['config'])

			if config_key in analysis['config_summaries']:
				summary = analysis['config_summaries'][config_key]
				print(
					f'\n{i}. Configuration: Altruism={altruism:.1f}, Tau={tau:.2f}, Fresh={fresh:.2f}, Mono={mono:.2f}'
				)
				print(
					f'   Total Score: {summary["total_score"]["mean"]:.2f} ± {summary["total_score"]["std"]:.2f}'
				)
				print(
					f'   Player10 Score: {summary["player10_score"]["mean"]:.2f} ± {summary["player10_score"]["std"]:.2f}'
				)
				rank_stats = summary.get('player10_rank', {})
				if rank_stats.get('count', 0):
					print(f'   Player10 Rank: {rank_stats["mean"]:.2f} ± {rank_stats["std"]:.2f}')
				else:
					print('   Player10 Rank: n/a')
				gap_stats = summary.get('player10_gap_to_best', {})
				if gap_stats.get('count', 0):
					print(f'   Gap to Best: {gap_stats["mean"]:.2f} ± {gap_stats["std"]:.2f}')
				else:
					print('   Gap to Best: n/a')
				print(
					f'   Avg Conversation Length: {summary["conversation_metrics"]["avg_length"]:.1f}'
				)
				print(
					f'   Early Termination Rate: {summary["conversation_metrics"]["early_termination_rate"]:.2f}'
				)
				print(
					f'   Avg Pause Count: {summary["conversation_metrics"]["avg_pause_count"]:.1f}'
				)
				print(
					f'   Avg Unique Items: {summary["conversation_metrics"]["avg_unique_items"]:.1f}'
				)

			# --- Full-parameterization aggregation and Top-10 table ---
			rows = summarize_parameterizations(results)

			print('\n=== TOP PARAMETERIZATIONS ===')
			summary_header = (
				f'{"Rank":<4} {"Label":<18} {"Total (μ±σ)":<16} '
				f'{"P10 (μ±σ)":<16} {"P10 Rank (μ±σ)":<20} {"Gap→Top (μ±σ)":<18} {"Count":<6}'
			)
			print(summary_header)
			print('-' * len(summary_header))

			top_rows = rows[:10]
			for i, row in enumerate(top_rows, start=1):
				label = parameter_label(row['meta'])
				total_stat = f'{row["mean"]:.2f}±{row["std"]:.2f}'
				p10_stat = f'{row["p10_mean"]:.2f}±{row["p10_std"]:.2f}'
				rank_stat = (
					f'{row["p10_rank_mean"]:.2f}±{row["p10_rank_std"]:.2f}'
					if row['p10_rank_mean'] is not None
					else 'n/a'
				)
				gap_stat = (
					f'{row["gap_mean"]:.2f}±{row["gap_std"]:.2f}'
					if row['gap_mean'] is not None
					else 'n/a'
				)
				print(
					f'{i:<4} {label:<18} {total_stat:<16} {p10_stat:<16} '
					f'{rank_stat:<20} {gap_stat:<18} {row["count"]:<6}'
				)

			print('\n=== PARAMETERIZATION DETAILS ===')
			for i, row in enumerate(top_rows, start=1):
				meta = row['meta']
				label = parameter_label(meta)
				diff_lines = difference_lines(meta)
				players_str = format_players(meta['players'])
				print(f'\n[{i}] {label}')
				rank_mean = row['p10_rank_mean']
				rank_std = row['p10_rank_std'] if row['p10_rank_std'] is not None else 0.0
				rank_text = f'{rank_mean:.2f} ± {rank_std:.2f}' if rank_mean is not None else 'n/a'
				gap_mean = row['gap_mean']
				gap_std = row['gap_std'] if row['gap_std'] is not None else 0.0
				gap_text = f'{gap_mean:.2f} ± {gap_std:.2f}' if gap_mean is not None else 'n/a'
				print(
					'  Scores: '
					f'total {row["mean"]:.2f} ± {row["std"]:.2f} | '
					f'P10 {row["p10_mean"]:.2f} ± {row["p10_std"]:.2f} | '
					f'rank {rank_text} | '
					f'gap {gap_text} | '
					f'runs {row["count"]}'
				)
				print(
					'  Core: '
					f'altruism={meta["altruism_prob"]:.2f}, '
					f'tau={meta["tau_margin"]:.2f}, '
					f'εfresh={meta["epsilon_fresh"]:.2f}, '
					f'εmono={meta["epsilon_mono"]:.2f}'
				)
				print(
					'  Weights: '
					f'min_samples={meta["min_samples_pid"]}, '
					f'ewma={meta["ewma_alpha"]:.2f}, '
					f'importance={meta["importance_weight"]:.2f}, '
					f'coherence={meta["coherence_weight"]:.2f}, '
					f'freshness={meta["freshness_weight"]:.2f}, '
					f'monotony={meta["monotony_weight"]:.2f}'
				)
				print(
					'  Schedule: '
					f'length={meta["conversation_length"]}, '
					f'subjects={meta["subjects"]}, '
					f'memory={meta["memory_size"]}, '
					f'players={players_str}'
				)
				if diff_lines:
					print('  Differences vs defaults:')
					for line in diff_lines:
						print(f'    - {line}')
				else:
					print('  Differences vs defaults: none')

			if not args.no_dashboard:
				dashboard_root = Path(config.output_dir or '.') / 'dashboards'
				dashboard_root.mkdir(parents=True, exist_ok=True)
				dashboard_path = generate_dashboard(
					results,
					analysis,
					config,
					dashboard_root,
				)
				if dashboard_path:
					print(f'\nInteractive dashboard opened: {dashboard_path}')
				else:
					print('\nPlotly not available; skipped dashboard generation.')

		# Overall stats across all runs
		all_scores = [r.total_score for r in results]
		overall_mean = sum(all_scores) / len(all_scores) if all_scores else 0.0
		overall_std = _std(all_scores) if all_scores else 0.0
		print(
			f'\nOverall Total Score: {overall_mean:.2f} ± {overall_std:.2f} across {len(all_scores)} runs'
		)


if __name__ == '__main__':
	main()
