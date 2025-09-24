"""Plotly dashboard builder for Player10 simulation results."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ..reporting import (
	difference_lines,
	format_players,
	parameter_label,
	summarize_parameterizations,
)


def _slugify(value: str | None) -> str:
	value = (value or 'run').strip().lower()
	value = re.sub(r'[^a-z0-9_-]+', '-', value)
	value = value.strip('-')
	return value or 'run'


def _format_stat(name: str, value: str | int | float) -> str:
	return (
		f'<div class="card"><div class="label">{name}</div><div class="value">{value}</div></div>'
	)


def _format_number(value: float | None, digits: int = 2) -> str:
	if value is None:
		return 'n/a'
	return f'{value:.{digits}f}'


COLORWAY = [
	'#3867d6',
	'#fa8231',
	'#20bf6b',
	'#a55eea',
	'#fed330',
	'#fc5c65',
	'#2d98da',
]

COMPONENT_LABELS = {
	'importance': 'Importance',
	'coherence': 'Coherence',
	'freshness': 'Freshness',
	'nonmonotonousness': 'Monotony relief',
}


def _config_value(result, attr: str):
	config = getattr(result, 'config', None)
	if config is None:
		return None
	if hasattr(config, attr):
		return getattr(config, attr)
	if isinstance(config, dict):
		return config.get(attr)
	return None


def _metric_value(result, metric: str):
	if metric == 'total_score':
		return getattr(result, 'total_score', None)
	if metric == 'player10_score':
		return getattr(result, 'player10_total_mean', None)
	if metric == 'player10_individual':
		return getattr(result, 'player10_individual_mean', None)
	if metric == 'early_termination':
		value = getattr(result, 'early_termination', None)
		if value is None:
			return None
		try:
			return float(value)
		except (TypeError, ValueError):
			return None
	return getattr(result, metric, None)


def _compute_heatmap_data(results, row_attr: str, col_attr: str, metric: str):
	matrix = defaultdict(lambda: defaultdict(list))
	rows: set = set()
	cols: set = set()
	for result in results:
		row_value = _config_value(result, row_attr)
		col_value = _config_value(result, col_attr)
		metric_value = _metric_value(result, metric)
		if row_value is None or col_value is None or metric_value is None:
			continue
		matrix[row_value][col_value].append(float(metric_value))
		rows.add(row_value)
		cols.add(col_value)
	if not rows or not cols:
		return None
	row_order = sorted(rows)
	col_order = sorted(cols)
	grid: list[list[float | None]] = []
	for row_value in row_order:
		row_data: list[float | None] = []
		for col_value in col_order:
			bucket = matrix.get(row_value, {}).get(col_value, [])
			if bucket:
				row_data.append(sum(bucket) / len(bucket))
			else:
				row_data.append(None)
		grid.append(row_data)
	return row_order, col_order, grid


def _collect_scores_by_altruism(results):
	buckets = defaultdict(lambda: {'total': [], 'player10': []})
	for result in results:
		altruism = _config_value(result, 'altruism_prob')
		if altruism is None:
			continue
		total_value = _metric_value(result, 'total_score')
		if total_value is not None:
			buckets[altruism]['total'].append(float(total_value))
		p10_value = _metric_value(result, 'player10_score')
		if p10_value is not None:
			buckets[altruism]['player10'].append(float(p10_value))
	if not buckets:
		return None
	return dict(sorted(buckets.items()))


def _component_means_by_altruism(results):
	sums = defaultdict(lambda: defaultdict(float))
	counts = defaultdict(lambda: defaultdict(int))
	for result in results:
		altruism = _config_value(result, 'altruism_prob')
		breakdown = getattr(result, 'score_breakdown', None) or {}
		if altruism is None:
			continue
		for key in COMPONENT_LABELS:
			value = breakdown.get(key)
			if value is None:
				continue
			try:
				value = float(value)
			except (TypeError, ValueError):
				continue
			sums[altruism][key] += value
			counts[altruism][key] += 1
	if not sums:
		return None
	altruism_values = sorted(sums.keys())
	component_series: dict[str, list[float]] = {key: [] for key in COMPONENT_LABELS}
	for altruism in altruism_values:
		for key in COMPONENT_LABELS:
			count = counts[altruism].get(key, 0)
			if count:
				component_series[key].append(sums[altruism][key] / count)
			else:
				component_series[key].append(0.0)
	return altruism_values, component_series


def _aggregate_pareto_points(results):
	groups = defaultdict(
		lambda: {
			'total_sum': 0.0,
			'total_count': 0,
			'p10_sum': 0.0,
			'p10_count': 0,
			'early_sum': 0.0,
			'early_count': 0,
		}
	)
	for result in results:
		key = (
			_config_value(result, 'altruism_prob'),
			_config_value(result, 'tau_margin'),
			_config_value(result, 'epsilon_fresh'),
			_config_value(result, 'epsilon_mono'),
		)
		if any(value is None for value in key):
			continue
		total_value = _metric_value(result, 'total_score')
		if total_value is not None:
			groups[key]['total_sum'] += float(total_value)
			groups[key]['total_count'] += 1
		p10_value = _metric_value(result, 'player10_individual')
		if p10_value is not None:
			groups[key]['p10_sum'] += float(p10_value)
			groups[key]['p10_count'] += 1
		early_value = _metric_value(result, 'early_termination')
		if early_value is not None:
			groups[key]['early_sum'] += float(early_value)
			groups[key]['early_count'] += 1
	points: list[dict[str, float | int | None]] = []
	for key, data in groups.items():
		if not data['total_count'] or not data['p10_count']:
			continue
		altruism, tau, fresh, mono = key
		point = {
			'altruism': altruism,
			'tau': tau,
			'fresh': fresh,
			'mono': mono,
			'total': data['total_sum'] / data['total_count'],
			'player10': data['p10_sum'] / data['p10_count'],
			'early': (data['early_sum'] / data['early_count']) if data['early_count'] else None,
			'runs': data['total_count'],
		}
		points.append(point)
	if not points:
		return None
	points.sort(key=lambda item: (item['altruism'], item['tau'], item['fresh'], item['mono']))
	return points


def _format_axis_value(value):
	if isinstance(value, float):
		formatted = f'{value:.3f}' if abs(value) < 1 else f'{value:.2f}'
		return formatted.rstrip('0').rstrip('.')
	return str(value)


def generate_dashboard(
	results,
	analysis,
	config,
	output_dir: Path,
	open_browser: bool = True,
) -> Path | None:
	"""Generate a Plotly dashboard summarizing the run and optionally open it."""
	try:
		import plotly.graph_objects as go
		import plotly.io as pio

		from plotly.subplots import make_subplots

	except ImportError:
		return None

	output_dir = Path(output_dir)
	output_dir.mkdir(parents=True, exist_ok=True)

	analysis = analysis or {}

	aggregated = summarize_parameterizations(results)
	table_rows: list[dict] = []
	for row in aggregated:
		meta = row['meta']
		label = parameter_label(meta)
		components = row.get('components', {})
		importance_stats = components.get('importance', {})
		coherence_stats = components.get('coherence', {})
		freshness_stats = components.get('freshness', {})
		monotony_stats = components.get('monotony', {})
		table_rows.append(
			{
				'label': label,
				'total_mean': row['mean'],
				'total_std': row['std'],
				'p10_mean': row['p10_mean'],
				'p10_std': row['p10_std'],
				'rank_mean': row['p10_rank_mean'],
				'rank_std': row['p10_rank_std'],
				'gap_mean': row['gap_mean'],
				'gap_std': row['gap_std'],
				'importance_mean': importance_stats.get('mean'),
				'coherence_mean': coherence_stats.get('mean'),
				'freshness_mean': freshness_stats.get('mean'),
				'monotony_mean': monotony_stats.get('mean'),
				'components': components,
				'count': row['count'],
				'players': format_players(meta['players']),
				'core': {
					'Altruism probability': _format_number(meta['altruism_prob']),
					'Tau margin': _format_number(meta['tau_margin']),
					'Epsilon fresh': _format_number(meta['epsilon_fresh']),
					'Epsilon mono': _format_number(meta['epsilon_mono']),
				},
				'weights': {
					'Min samples PID': meta['min_samples_pid'],
					'EWMA alpha': _format_number(meta['ewma_alpha']),
					'Importance weight': _format_number(meta['importance_weight']),
					'Coherence weight': _format_number(meta['coherence_weight']),
					'Freshness weight': _format_number(meta['freshness_weight']),
					'Monotony weight': _format_number(meta['monotony_weight']),
				},
				'schedule': {
					'Conversation length': meta['conversation_length'],
					'Subjects': meta['subjects'],
					'Memory size': _format_number(meta['memory_size'], 0),
					'Players': format_players(meta['players']),
				},
				'differences': difference_lines(meta),
			}
		)

	top_rows = aggregated[:10]
	rank_values = [r.player10_rank_mean for r in results if r.player10_rank_mean is not None]
	gap_values = [r.player10_gap_to_best for r in results if r.player10_gap_to_best is not None]
	total_scores = [r.total_score for r in results]

	generated_at = datetime.now()
	timestamp = generated_at.strftime('%Y%m%d_%H%M%S')
	slug = _slugify(getattr(config, 'name', 'run'))
	output_path = output_dir / f'{timestamp}_{slug}_dashboard.html'

	chart_sections: list[dict[str, str]] = []

	if top_rows:
		fig_top = go.Figure()
		rank_labels: list[str] = []
		for idx, row in enumerate(top_rows, start=1):
			full_label = parameter_label(row['meta'])
			mean_value = row['mean']
			std_value = row.get('std', 0.0)
			rank_label = f'#{idx}'
			rank_labels.append(rank_label)
			fig_top.add_trace(
				go.Bar(
					x=[mean_value],
					y=[rank_label],
					orientation='h',
					name=full_label,
					marker=dict(color=COLORWAY[(idx - 1) % len(COLORWAY)]),
					text=[f'{mean_value:.2f} ± {std_value:.2f}'],
					textposition='outside',
					customdata=[[full_label, std_value]],
					hovertemplate=(
						'%{customdata[0]}<br>Mean: %{x:.2f}<br>Std: %{customdata[1]:.2f}<extra></extra>'
					),
				)
			)
		fig_top.update_layout(
			title='Top Parameterizations by Total Score',
			xaxis_title='Mean total score',
			yaxis_title='Rank',
			yaxis=dict(categoryorder='array', categoryarray=rank_labels),
			margin=dict(l=0, r=20, t=60, b=40),
			height=max(320, 90 * len(rank_labels)),
			uniformtext_minsize=10,
			uniformtext_mode='hide',
			legend=dict(
				title='Parameterization label',
				yanchor='top',
				y=1.0,
				xanchor='left',
				x=1.02,
				bgcolor='rgba(255,255,255,0.85)',
				bordercolor='rgba(0,0,0,0.1)',
				borderwidth=1,
			),
		)
		chart_sections.append(
			{
				'title': 'Top Parameterizations',
				'description': 'Mean total score (±σ) for the leading parameter sets. '
				'Track how tuning shifts impact headline performance.',
				'html': pio.to_html(
					fig_top,
					include_plotlyjs='cdn',
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='420px',
				),
			},
		)

	if rank_values:
		fig_rank = go.Figure(go.Histogram(x=rank_values, nbinsx=min(10, len(set(rank_values)))))
		fig_rank.update_layout(
			title='Player10 Finishing Rank Distribution',
			xaxis_title='Average finishing rank (1 = best)',
			yaxis_title='Occurrences',
		)
		chart_sections.append(
			{
				'title': 'Rank Distribution',
				'description': 'How often Player10 lands in each finishing position across runs.',
				'html': pio.to_html(
					fig_rank,
					include_plotlyjs=False,
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='360px',
				),
			},
		)

	if gap_values:
		fig_gap = go.Figure(go.Histogram(x=gap_values, nbinsx=min(10, len(set(gap_values)))))
		fig_gap.update_layout(
			title='Gap to Top Score',
			xaxis_title='Score gap compared to top performer',
			yaxis_title='Occurrences',
		)
		chart_sections.append(
			{
				'title': 'Gap to Top Score',
				'description': 'Distribution of how far Player10 lags behind the best player in each run.',
				'html': pio.to_html(
					fig_gap,
					include_plotlyjs=False,
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='360px',
				),
			},
		)

	if rank_values and gap_values:
		fig_scatter = go.Figure(
			go.Scatter(
				x=rank_values[: len(gap_values)],
				y=gap_values,
				mode='markers',
				marker=dict(size=8, color=gap_values, colorscale='Viridis', showscale=True),
				text=[f'Run {idx + 1}' for idx in range(len(gap_values))],
			)
		)
		fig_scatter.update_layout(
			title='Rank vs Gap (Per Run)',
			xaxis_title='Average rank',
			yaxis_title='Gap to top score',
		)
		chart_sections.append(
			{
				'title': 'Rank vs Gap',
				'description': 'Each dot represents a simulation: lower ranks and smaller gaps indicate stronger relative performance.',
				'html': pio.to_html(
					fig_scatter,
					include_plotlyjs=False,
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='360px',
				),
			},
		)

	# Enhanced analysis sections derived from notebook utilities
	heatmap_data = _compute_heatmap_data(results, 'altruism_prob', 'tau_margin', 'total_score')
	if heatmap_data:
		row_values, col_values, matrix = heatmap_data
		y_labels = [_format_axis_value(value) for value in row_values]
		x_labels = [_format_axis_value(value) for value in col_values]
		fig_heatmap = go.Figure(
			go.Heatmap(
				z=matrix,
				x=x_labels,
				y=y_labels,
				colorscale='Viridis',
				colorbar={'title': 'Mean total score'},
			)
		)
		fig_heatmap.update_layout(
			title='Total Score Heatmap',
			xaxis_title='Tau margin',
			yaxis_title='Altruism probability',
			margin={'l': 80, 'r': 40, 't': 60, 'b': 60},
		)
		chart_sections.append(
			{
				'title': 'Parameter Heatmap',
				'description': 'Average total score for each altruism/tau combination helps spot sweet spots quickly.',
				'html': pio.to_html(
					fig_heatmap,
					include_plotlyjs=False,
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='420px',
				),
			},
		)

	score_buckets = _collect_scores_by_altruism(results)
	if score_buckets:
		fig_dist = make_subplots(rows=1, cols=2, subplot_titles=('Total score', 'Player10 score'))
		for idx, (prob, values) in enumerate(score_buckets.items()):
			label = f'altruism {prob:.2f}' if isinstance(prob, float) else f'altruism {prob}'
			color = COLORWAY[idx % len(COLORWAY)]
			if values['total']:
				fig_dist.add_trace(
					go.Histogram(
						x=values['total'],
						name=label,
						legendgroup=label,
						marker={'color': color},
						opacity=0.55,
						nbinsx=20,
						showlegend=True,
					),
					row=1,
					col=1,
				)
			if values['player10']:
				fig_dist.add_trace(
					go.Histogram(
						x=values['player10'],
						name=label,
						legendgroup=label,
						marker={'color': color},
						opacity=0.55,
						nbinsx=20,
						showlegend=False,
					),
					row=1,
					col=2,
				)
		fig_dist.update_layout(
			title_text='Score Distributions by Altruism',
			barmode='overlay',
			legend={'orientation': 'h', 'y': 1.12, 'x': 0.5, 'xanchor': 'center'},
			xaxis_title='Total score',
			xaxis2_title='Player10 score',
			yaxis_title='Frequency',
			margin={'l': 60, 'r': 20, 't': 80, 'b': 60},
		)
		chart_sections.append(
			{
				'title': 'Score Distributions',
				'description': 'Histogram overlays reveal how each altruism setting shifts total and individual score shapes.',
				'html': pio.to_html(
					fig_dist,
					include_plotlyjs=False,
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='420px',
				),
			},
		)

	component_data = _component_means_by_altruism(results)
	if component_data:
		altruism_values, component_series = component_data
		labels = [_format_axis_value(value) for value in altruism_values]
		fig_components = go.Figure()
		for idx, (comp_key, comp_label) in enumerate(COMPONENT_LABELS.items()):
			values = component_series.get(comp_key, [])
			if not values:
				continue
			fig_components.add_trace(
				go.Bar(
					x=labels,
					y=values,
					name=comp_label,
					marker={'color': COLORWAY[idx % len(COLORWAY)]},
				)
			)
		fig_components.update_layout(
			title='Shared Component Breakdown',
			barmode='stack',
			xaxis_title='Altruism probability',
			yaxis_title='Mean shared score',
			legend={'orientation': 'h', 'y': 1.1, 'x': 0.5, 'xanchor': 'center'},
			margin={'l': 60, 'r': 20, 't': 80, 'b': 60},
		)
		chart_sections.append(
			{
				'title': 'Shared Components',
				'description': 'Stacks quantify how shared scoring components vary with altruism levels.',
				'html': pio.to_html(
					fig_components,
					include_plotlyjs=False,
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='420px',
				),
			},
		)

	pareto_points = _aggregate_pareto_points(results)
	if pareto_points:
		customdata = [
			[
				_format_axis_value(point['altruism']),
				_format_axis_value(point['tau']),
				_format_axis_value(point['fresh']),
				_format_axis_value(point['mono']),
				(f'{point["early"]:.1%}' if point['early'] is not None else 'n/a'),
				point['runs'],
			]
			for point in pareto_points
		]
		fig_pareto = go.Figure(
			go.Scatter(
				x=[point['player10'] for point in pareto_points],
				y=[point['total'] for point in pareto_points],
				mode='markers',
				marker={
					'size': 10,
					'color': [point['altruism'] for point in pareto_points],
					'colorscale': 'Viridis',
					'showscale': True,
					'colorbar': {'title': 'Altruism p'},
				},
				text=['ET>0.3' if (point['early'] or 0) > 0.3 else '' for point in pareto_points],
				textposition='top center',
				customdata=customdata,
				hovertemplate=(
					'Player10 mean: %{x:.2f}<br>'
					'Total mean: %{y:.2f}<br>'
					'Altruism: %{customdata[0]}<br>'
					'Tau margin: %{customdata[1]}<br>'
					'Epsilon fresh: %{customdata[2]}<br>'
					'Epsilon mono: %{customdata[3]}<br>'
					'Early termination: %{customdata[4]}<br>'
					'Runs: %{customdata[5]}<extra></extra>'
				),
			)
		)
		fig_pareto.update_layout(
			title='Pareto: Player10 vs Total Score',
			xaxis_title='Player10 individual mean',
			yaxis_title='Total score mean',
			margin={'l': 60, 'r': 20, 't': 60, 'b': 60},
		)
		chart_sections.append(
			{
				'title': 'Pareto Trade-off',
				'description': 'Scatter highlights where individual gains align with team score, colored by altruism.',
				'html': pio.to_html(
					fig_pareto,
					include_plotlyjs=False,
					full_html=False,
					config={'displaylogo': False},
					default_width='100%',
					default_height='420px',
				),
			},
		)

	total_simulations = analysis.get('total_simulations', len(results))
	unique_configs = analysis.get('unique_configurations', len(aggregated))
	best_entry = next(iter(analysis.get('best_configurations', [])), None)
	best_score = f'{best_entry["mean_score"]:.2f}' if best_entry else 'n/a'
	avg_rank = _format_number(sum(rank_values) / len(rank_values)) if rank_values else 'n/a'
	avg_gap = _format_number(sum(gap_values) / len(gap_values)) if gap_values else 'n/a'
	mean_total = _format_number(sum(total_scores) / len(total_scores)) if total_scores else 'n/a'

	metrics_html = ''.join(
		[
			_format_stat('Total simulations', total_simulations),
			_format_stat('Unique configurations', unique_configs),
			_format_stat('Average total score', mean_total),
			_format_stat('Best configuration score', best_score),
			_format_stat('Player10 avg rank', avg_rank),
			_format_stat('Player10 avg gap', avg_gap),
		]
	)

	title = getattr(config, 'name', 'Player10 Monte Carlo') or 'Player10 Monte Carlo'
	description = getattr(config, 'description', '') or ''

	table_json = json.dumps(table_rows)
	charts_html = ''.join(
		(
			'<div class="figure-wrapper">'
			+ f'<h2>{section["title"]}</h2>'
			+ f'<p class="figure-description">{section["description"]}</p>'
			+ section['html']
			+ '</div>'
		)
		for section in chart_sections
	)

	html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title} – Player10 Dashboard</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css" />
<style>
	body {{ font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 24px; background: #f2f4f8; color: #1f2933; }}
	h1 {{ margin-top: 0; font-size: 2.2rem; }}
	.section {{ margin-bottom: 32px; }}
	.cards {{ display: flex; flex-wrap: wrap; gap: 16px; }}
	.card {{ background: #ffffff; border-radius: 10px; padding: 16px 20px; box-shadow: 0 8px 18px rgba(31, 41, 51, 0.08); min-width: 180px; }}
	.card .label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #52606d; margin-bottom: 6px; }}
	.card .value {{ font-size: 1.4rem; font-weight: 600; color: #102a43; }}
	.figure-wrapper {{ background: #ffffff; border-radius: 12px; padding: 12px 16px; box-shadow: 0 8px 20px rgba(31, 41, 51, 0.12); margin-bottom: 24px; }}
	.figure-wrapper h2 {{ margin: 0 0 8px 0; font-size: 1.2rem; color: #243b53; }}
	.figure-description {{ margin: 0 0 12px 0; color: #52606d; font-size: 0.95rem; }}
	.meta {{ color: #52606d; font-size: 0.95rem; margin-bottom: 16px; }}
	#parameter-table_wrapper {{ background: #ffffff; border-radius: 12px; padding: 16px; box-shadow: 0 8px 18px rgba(31, 41, 51, 0.08); }}
	.detail-panel {{ background: #ffffff; border-radius: 12px; padding: 20px; box-shadow: 0 8px 20px rgba(31, 41, 51, 0.12); margin-top: 24px; display: none; }}
	.detail-panel.active {{ display: block; }}
	.detail-panel h2 {{ margin-top: 0; }}
	.detail-section {{ margin-bottom: 16px; }}
	.detail-section h3 {{ margin: 0 0 8px 0; font-size: 1.05rem; color: #243b53; }}
	.detail-list {{ margin: 0; padding-left: 18px; color: #334e68; }}
</style>
</head>
<body>
	<h1>{title}</h1>
	<div class="meta">Generated {generated_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
	{f'<p class="meta">{description}</p>' if description else ''}

	<div class="section">
		<div class="cards">{metrics_html}</div>
	</div>

	<div class="section">
		<h2>Parameterizations</h2>
		<p class="meta">Click column headers to sort. Select a row to inspect the configuration details.</p>
		<table id="parameter-table" class="display" style="width:100%">
			<thead>
				<tr>
					<th title="Parameter label highlighting deviations from defaults.">Label</th>
					<th title="Average total score across all runs for this parameterization.">Total μ</th>
					<th title="Standard deviation of total score across runs.">Total σ</th>
					<th title="Average Player10 total score across runs.">P10 μ</th>
					<th title="Standard deviation of Player10 total score.">P10 σ</th>
					<th title="Average finishing rank (1 = best).">Rank μ</th>
					<th title="Average score gap between Player10 and the top player.">Gap μ</th>
					<th title="Mean importance component contribution.">Importance μ</th>
					<th title="Mean coherence component contribution.">Coherence μ</th>
					<th title="Mean freshness component contribution.">Freshness μ</th>
					<th title="Mean monotony component contribution (penalty).">Monotony μ</th>
					<th title="Number of simulations aggregated for this row.">Runs</th>
					<th title="Player roster for the simulations.">Players</th>
				</tr>
			</thead>
			<tbody></tbody>
		</table>

		<div id="detail-panel" class="detail-panel">
			<h2 id="detail-title">Select a parameterization</h2>
			<div id="detail-content"></div>
		</div>
	</div>

	{charts_html}

	<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
	<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
	<script type="application/json" id="table-data">{table_json}</script>
	<script>
	(function() {{
		const data = JSON.parse(document.getElementById('table-data').textContent);
		const fmt = function (val) {{
			return typeof val === 'number' ? val.toFixed(2) : 'n/a';
		}};
		const table = $('#parameter-table').DataTable({{
			data,
			columns: [
				{{ data: 'label' }},
				{{ data: 'total_mean', render: fmt }},
				{{ data: 'total_std', render: fmt }},
				{{ data: 'p10_mean', render: fmt }},
				{{ data: 'p10_std', render: fmt }},
				{{ data: 'rank_mean', render: fmt }},
				{{ data: 'gap_mean', render: fmt }},
				{{ data: 'importance_mean', render: fmt }},
				{{ data: 'coherence_mean', render: fmt }},
				{{ data: 'freshness_mean', render: fmt }},
				{{ data: 'monotony_mean', render: fmt }},
				{{ data: 'count' }},
				{{ data: 'players' }},
			],
			order: [[1, 'desc']],
			pageLength: 15
		}});

		const detailPanel = document.getElementById('detail-panel');
		const detailTitle = document.getElementById('detail-title');
		const detailContent = document.getElementById('detail-content');

		$('#parameter-table tbody').on('click', 'tr', function () {{
			const rowData = table.row(this).data();
			if (!rowData) return;
			updateDetail(rowData);
		}});

		function renderSection(title, items) {{
			if (!items || (Array.isArray(items) && !items.length)) return '';
			let listItems = '';
			if (Array.isArray(items)) {{
				listItems = items
					.map(function (item) {{
						return '<li>' + item + '</li>';
					}})
					.join('');
			}} else {{
				listItems = Object.entries(items)
					.map(function ([key, value]) {{
						return '<li><strong>' + key + ':</strong> ' + value + '</li>';
					}})
					.join('');
			}}
			return (
				'<div class="detail-section">'
				+ '<h3>' + title + '</h3>'
				+ '<ul class="detail-list">' + listItems + '</ul>'
				+ '</div>'
			);
		}}

		const componentLabels = {{
			importance: 'Importance',
			coherence: 'Coherence',
			freshness: 'Freshness',
			monotony: 'Monotony',
		}};

		function renderComponentSection(components) {{
			if (!components || Object.keys(components).length === 0) return '';
			const items = Object.entries(components)
				.map(function ([key, stats]) {{
					const label = componentLabels[key] || (key.charAt(0).toUpperCase() + key.slice(1));
					const mean = stats && typeof stats.mean === 'number' ? stats.mean : null;
					const std = stats && typeof stats.std === 'number' ? stats.std : null;
					return '<li><strong>' + label + ':</strong> ' + numberPair(mean, std) + '</li>';
				}})
				.join('');
			return (
				'<div class="detail-section">'
				+ '<h3>Score components</h3>'
				+ '<ul class="detail-list">' + items + '</ul>'
				+ '</div>'
			);
		}}

		function updateDetail(row) {{
			detailTitle.textContent = row.label;
			const summary = (
				'<ul class="detail-list">'
				+ '<li><strong>Total μ±σ:</strong> ' + numberPair(row.total_mean, row.total_std) + '</li>'
				+ '<li><strong>Player10 μ±σ:</strong> ' + numberPair(row.p10_mean, row.p10_std) + '</li>'
				+ '<li><strong>Rank μ±σ:</strong> ' + numberPair(row.rank_mean, row.rank_std) + '</li>'
				+ '<li><strong>Gap μ±σ:</strong> ' + numberPair(row.gap_mean, row.gap_std) + '</li>'
				+ '<li><strong>Runs:</strong> ' + row.count + '</li>'
				+ '</ul>'
			);
			const componentSection = renderComponentSection(row.components);
			const differences = row.differences && row.differences.length
				? renderSection('Differences vs defaults', row.differences)
				: '';
			detailContent.innerHTML = summary
				+ renderSection('Core parameters', row.core)
				+ renderSection('Weights', row.weights)
				+ renderSection('Schedule', row.schedule)
				+ componentSection
				+ differences;
			detailPanel.classList.add('active');
		}}

		function numberPair(mean, std) {{
			const m = mean !== null && mean !== undefined ? Number(mean).toFixed(2) : 'n/a';
			const s = std !== null && std !== undefined ? Number(std).toFixed(2) : 'n/a';
			return m + ' ± ' + s;
		}}
	}})();
	</script>
</body>
</html>
"""

	output_path.write_text(html, encoding='utf-8')

	if open_browser:
		try:
			import webbrowser

			webbrowser.open(output_path.resolve().as_uri())
		except Exception:
			pass

	return output_path
