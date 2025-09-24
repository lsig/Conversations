"""Shared reporting utilities for Player10 CLI and dashboards.

Provides helpers to summarize simulation results, format configuration
explanations, and build short labels for parameterizations.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

try:
	from ..sim.test_framework import (
		ParameterRange,
		TestConfiguration,
	)
except ModuleNotFoundError:
	ParameterRange = None  # type: ignore
	TestConfiguration = None  # type: ignore
	_BASELINE_CONFIG = None
else:
	_BASELINE_CONFIG = TestConfiguration(name='baseline_snapshot')


def _first(range_field) -> Any:
	if range_field is None:
		return None
	return range_field.values[0] if getattr(range_field, 'values', None) else None


def _capture_baseline_meta() -> dict[str, Any]:
	if _BASELINE_CONFIG is None:
		return {
			'altruism_prob': 0.0,
			'tau_margin': 0.0,
			'epsilon_fresh': 0.0,
			'epsilon_mono': 0.0,
			'min_samples_pid': 5,
			'ewma_alpha': 0.0,
			'importance_weight': 1.0,
			'coherence_weight': 1.0,
			'freshness_weight': 1.0,
			'monotony_weight': 1.0,
			'conversation_length': 0,
			'subjects': 0,
			'memory_size': 0,
			'players': {},
		}
	players = dict(_BASELINE_CONFIG.player_configs[0]) if _BASELINE_CONFIG.player_configs else {}
	return {
		'altruism_prob': _first(_BASELINE_CONFIG.altruism_probs),
		'tau_margin': _first(_BASELINE_CONFIG.tau_margins),
		'epsilon_fresh': _first(_BASELINE_CONFIG.epsilon_fresh_values),
		'epsilon_mono': _first(_BASELINE_CONFIG.epsilon_mono_values),
		'min_samples_pid': _first(_BASELINE_CONFIG.min_samples_values),
		'ewma_alpha': _first(_BASELINE_CONFIG.ewma_alpha_values),
		'importance_weight': _first(_BASELINE_CONFIG.importance_weights),
		'coherence_weight': _first(_BASELINE_CONFIG.coherence_weights),
		'freshness_weight': _first(_BASELINE_CONFIG.freshness_weights),
		'monotony_weight': _first(_BASELINE_CONFIG.monotony_weights),
		'conversation_length': _BASELINE_CONFIG.conversation_length,
		'subjects': _BASELINE_CONFIG.subjects,
		'memory_size': _BASELINE_CONFIG.memory_size,
		'players': players,
	}


BASELINE_META = _capture_baseline_meta()


def normalize_players(players: dict[str, int]) -> tuple[tuple[str, int], ...]:
	return tuple(sorted(players.items()))


def format_players(players: dict[str, int]) -> str:
	return ', '.join(f'{key}={value}' for key, value in sorted(players.items())) or 'none'


_PARAM_FIELD_SPECS: list[tuple[str, str, str, str, int]] = [
	('altruism_prob', 'Altruism probability', 'A', 'float', 2),
	('tau_margin', 'Tau margin', 'T', 'float', 2),
	('epsilon_fresh', 'Freshness epsilon', 'Ef', 'float', 2),
	('epsilon_mono', 'Monotony epsilon', 'Em', 'float', 2),
	('min_samples_pid', 'Min samples', 'Ms', 'int', 0),
	('ewma_alpha', 'EWMA alpha', 'Ew', 'float', 2),
	('importance_weight', 'Importance weight', 'Wi', 'float', 2),
	('coherence_weight', 'Coherence weight', 'Wc', 'float', 2),
	('freshness_weight', 'Freshness weight', 'Wf', 'float', 2),
	('monotony_weight', 'Monotony weight', 'Wm', 'float', 2),
	('conversation_length', 'Conversation length', 'Len', 'int', 0),
	('subjects', 'Subjects', 'Sub', 'int', 0),
	('memory_size', 'Memory size', 'Mem', 'int', 0),
]


def _float_differs(a: float, b: float) -> bool:
	return not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _std(values: list[float]) -> float:
	if len(values) < 2:
		return 0.0
	mean = sum(values) / len(values)
	variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
	return variance**0.5


def parameter_label(meta: dict[str, Any], baseline: dict[str, Any] | None = None) -> str:
	baseline = baseline or BASELINE_META
	tokens: list[str] = []
	for key, _label, short, kind, precision in _PARAM_FIELD_SPECS:
		value = meta.get(key)
		base = baseline.get(key)
		if kind == 'float' and isinstance(value, float) and isinstance(base, float):
			if _float_differs(value, base):
				delta = value - base
				tokens.append(f'{short}{delta:+.{precision}f}')
		elif kind == 'int' and isinstance(value, int) and isinstance(base, int) and value != base:
			delta = value - base
			tokens.append(f'{short}{delta:+d}')

	if normalize_players(meta.get('players', {})) != normalize_players(baseline.get('players', {})):
		tokens.append('Players')

	return ', '.join(tokens) if tokens else 'default'


def difference_lines(meta: dict[str, Any], baseline: dict[str, Any] | None = None) -> list[str]:
	baseline = baseline or BASELINE_META
	lines: list[str] = []
	for key, label, _short, kind, precision in _PARAM_FIELD_SPECS:
		value = meta.get(key)
		base = baseline.get(key)
		if kind == 'float' and isinstance(value, float) and isinstance(base, float):
			if _float_differs(value, base):
				delta = value - base
				value_fmt = f'{value:.{precision}f}'
				delta_fmt = f'{delta:+.{precision}f}'
				base_fmt = f'{base:.{precision}f}'
				lines.append(f'{label}: {value_fmt} ({delta_fmt} vs {base_fmt})')
		elif kind == 'int' and isinstance(value, int) and isinstance(base, int) and value != base:
			delta = value - base
			lines.append(f'{label}: {value} ({delta:+d} vs {base})')

	players_current = meta.get('players', {})
	players_default = baseline.get('players', {})
	if normalize_players(players_current) != normalize_players(players_default):
		lines.append(
			f'Players: {format_players(players_current)} (default {format_players(players_default)})'
		)

	return lines


def summarize_parameterizations(results) -> list[dict[str, Any]]:
	"""Aggregate results by full parameterization with extended metrics."""
	groups: dict[tuple, dict[str, Any]] = {}
	by_key_scores: dict[tuple, list[float]] = defaultdict(list)
	by_key_p10: dict[tuple, list[float]] = defaultdict(list)
	by_key_p10_rank: dict[tuple, list[float]] = defaultdict(list)
	by_key_gap: dict[tuple, list[float]] = defaultdict(list)
	component_values: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

	def _players_key(players_dict: dict[str, int]) -> tuple:
		return tuple(sorted(players_dict.items()))

	def _key_from_cfg(cfg) -> tuple:
		return (
			round(cfg.altruism_prob, 6),
			round(cfg.tau_margin, 6),
			round(cfg.epsilon_fresh, 6),
			round(cfg.epsilon_mono, 6),
			int(cfg.min_samples_pid),
			round(cfg.ewma_alpha, 6),
			round(cfg.importance_weight, 6),
			round(cfg.coherence_weight, 6),
			round(cfg.freshness_weight, 6),
			round(cfg.monotony_weight, 6),
			_players_key(cfg.players),
			cfg.conversation_length,
			cfg.subjects,
			cfg.memory_size,
		)

	for result in results:
		key = _key_from_cfg(result.config)
		if key not in groups:
			groups[key] = {
				'altruism_prob': result.config.altruism_prob,
				'tau_margin': result.config.tau_margin,
				'epsilon_fresh': result.config.epsilon_fresh,
				'epsilon_mono': result.config.epsilon_mono,
				'min_samples_pid': result.config.min_samples_pid,
				'ewma_alpha': result.config.ewma_alpha,
				'importance_weight': result.config.importance_weight,
				'coherence_weight': result.config.coherence_weight,
				'freshness_weight': result.config.freshness_weight,
				'monotony_weight': result.config.monotony_weight,
				'players': result.config.players,
				'conversation_length': result.config.conversation_length,
				'subjects': result.config.subjects,
				'memory_size': result.config.memory_size,
			}
		by_key_scores[key].append(result.total_score)
		by_key_p10[key].append(result.player_scores.get('Player10', 0.0))
		if result.player10_rank_mean is not None:
			by_key_p10_rank[key].append(result.player10_rank_mean)
		if result.player10_gap_to_best is not None:
			by_key_gap[key].append(result.player10_gap_to_best)
		for component, value in getattr(result, 'score_breakdown', {}).items():
			if component == 'total':
				continue
			try:
				component_values[key][component].append(float(value))
			except (TypeError, ValueError):
				continue

	rows: list[dict[str, Any]] = []
	for key, meta in groups.items():
		scores = by_key_scores[key]
		p10_scores = by_key_p10[key]
		rank_values = by_key_p10_rank.get(key, [])
		gap_values = by_key_gap.get(key, [])
		components_stats: dict[str, dict[str, float]] = {}
		for component, values in component_values.get(key, {}).items():
			if not values:
				continue
			components_stats[component] = {
				'mean': sum(values) / len(values),
				'std': _std(values),
			}
		rows.append(
			{
				'key': key,
				'meta': meta,
				'mean': sum(scores) / len(scores),
				'std': _std(scores),
				'count': len(scores),
				'p10_mean': (sum(p10_scores) / len(p10_scores)) if p10_scores else 0.0,
				'p10_std': _std(p10_scores) if p10_scores else 0.0,
				'p10_rank_mean': (sum(rank_values) / len(rank_values)) if rank_values else None,
				'p10_rank_std': _std(rank_values) if rank_values else None,
				'gap_mean': (sum(gap_values) / len(gap_values)) if gap_values else None,
				'gap_std': _std(gap_values) if gap_values else None,
				'components': components_stats,
			}
		)

	rows.sort(key=lambda row: row['mean'], reverse=True)
	return rows


__all__ = [
	'BASELINE_META',
	'format_players',
	'normalize_players',
	'parameter_label',
	'difference_lines',
	'summarize_parameterizations',
]
