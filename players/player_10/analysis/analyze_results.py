"""
Results analysis and visualization tools for Monte Carlo simulations.

This module provides tools to analyze simulation results and create visualizations
to understand the performance of different Player10 configurations.
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from ..sim.monte_carlo import MonteCarloSimulator, SimulationResult


class ResultsAnalyzer:
	"""Analyzer for Monte Carlo simulation results."""

	def __init__(self, results_file: str = None):
		"""
		Initialize the analyzer.

		Args:
			results_file: Path to results JSON file to load
		"""
		self.simulator = MonteCarloSimulator()
		self.results: list[SimulationResult] = []

		if results_file:
			self.load_results(results_file)

	def load_results(self, filename: str):
		"""Load results from a JSON file."""
		self.results = self.simulator.load_results(filename)
		print(f'Loaded {len(self.results)} simulation results')

	def create_dataframe(self) -> pd.DataFrame:
		"""Convert results to a pandas DataFrame for analysis."""
		data = []

		for result in self.results:
			row = {
				'altruism_prob': result.config.altruism_prob,
				'tau_margin': result.config.tau_margin,
				'epsilon_fresh': result.config.epsilon_fresh,
				'epsilon_mono': result.config.epsilon_mono,
				'seed': result.config.seed,
				'total_score': result.total_score,
				'player10_score': result.player_scores.get('Player10', 0),
				'conversation_length': result.conversation_length,
				'early_termination': result.early_termination,
				'pause_count': result.pause_count,
				'unique_items_used': result.unique_items_used,
				'execution_time': result.execution_time,
			}
			data.append(row)

		return pd.DataFrame(data)

	def plot_altruism_comparison(self, save_path: str = None):
		"""Create plots comparing different altruism probabilities."""
		if not self.results:
			print('No results loaded. Please load results first.')
			return

		df = self.create_dataframe()

		# Group by altruism probability
		altruism_groups = (
			df.groupby('altruism_prob')
			.agg(
				{
					'total_score': ['mean', 'std', 'count'],
					'player10_score': ['mean', 'std'],
					'conversation_length': 'mean',
					'early_termination': 'mean',
					'pause_count': 'mean',
				}
			)
			.round(3)
		)

		# Create subplots
		fig, axes = plt.subplots(2, 2, figsize=(15, 10))
		fig.suptitle('Player10 Altruism Probability Comparison', fontsize=16)

		# Plot 1: Total Score vs Altruism Probability
		ax1 = axes[0, 0]
		altruism_probs = altruism_groups.index
		mean_scores = altruism_groups[('total_score', 'mean')]
		std_scores = altruism_groups[('total_score', 'std')]

		ax1.errorbar(
			altruism_probs, mean_scores, yerr=std_scores, marker='o', capsize=5, capthick=2
		)
		ax1.set_xlabel('Altruism Probability')
		ax1.set_ylabel('Total Score')
		ax1.set_title('Total Score vs Altruism Probability')
		ax1.grid(True, alpha=0.3)

		# Plot 2: Player10 Score vs Altruism Probability
		ax2 = axes[0, 1]
		mean_p10_scores = altruism_groups[('player10_score', 'mean')]
		std_p10_scores = altruism_groups[('player10_score', 'std')]

		ax2.errorbar(
			altruism_probs,
			mean_p10_scores,
			yerr=std_p10_scores,
			marker='s',
			capsize=5,
			capthick=2,
			color='orange',
		)
		ax2.set_xlabel('Altruism Probability')
		ax2.set_ylabel('Player10 Score')
		ax2.set_title('Player10 Individual Score vs Altruism Probability')
		ax2.grid(True, alpha=0.3)

		# Plot 3: Conversation Length vs Altruism Probability
		ax3 = axes[1, 0]
		conv_lengths = altruism_groups[('conversation_length', 'mean')]
		ax3.plot(altruism_probs, conv_lengths, marker='^', color='green')
		ax3.set_xlabel('Altruism Probability')
		ax3.set_ylabel('Average Conversation Length')
		ax3.set_title('Conversation Length vs Altruism Probability')
		ax3.grid(True, alpha=0.3)

		# Plot 4: Early Termination Rate vs Altruism Probability
		ax4 = axes[1, 1]
		early_term_rates = altruism_groups[('early_termination', 'mean')]
		ax4.plot(altruism_probs, early_term_rates, marker='d', color='red')
		ax4.set_xlabel('Altruism Probability')
		ax4.set_ylabel('Early Termination Rate')
		ax4.set_title('Early Termination Rate vs Altruism Probability')
		ax4.grid(True, alpha=0.3)

		plt.tight_layout()

		if save_path:
			plt.savefig(save_path, dpi=300, bbox_inches='tight')
			print(f'Plot saved to: {save_path}')

		plt.show()

	def plot_parameter_heatmap(
		self, param1: str, param2: str, metric: str = 'total_score', save_path: str = None
	):
		"""Create a heatmap showing the interaction between two parameters."""
		if not self.results:
			print('No results loaded. Please load results first.')
			return

		df = self.create_dataframe()

		# Create pivot table
		pivot = df.groupby([param1, param2])[metric].mean().unstack()

		# Create heatmap
		plt.figure(figsize=(10, 8))
		sns.heatmap(pivot, annot=True, fmt='.2f', cmap='viridis')
		plt.title(f'{metric.title()} Heatmap: {param1} vs {param2}')
		plt.xlabel(param2.replace('_', ' ').title())
		plt.ylabel(param1.replace('_', ' ').title())

		if save_path:
			plt.savefig(save_path, dpi=300, bbox_inches='tight')
			print(f'Heatmap saved to: {save_path}')

		plt.show()

	def plot_score_distributions(self, save_path: str = None):
		"""Plot score distributions for different configurations."""
		if not self.results:
			print('No results loaded. Please load results first.')
			return

		df = self.create_dataframe()

		# Get unique altruism probabilities
		altruism_probs = sorted(df['altruism_prob'].unique())

		fig, axes = plt.subplots(1, 2, figsize=(15, 6))
		fig.suptitle('Score Distributions by Altruism Probability', fontsize=16)

		# Plot 1: Total Score Distributions
		ax1 = axes[0]
		for prob in altruism_probs:
			scores = df[df['altruism_prob'] == prob]['total_score']
			ax1.hist(scores, alpha=0.6, label=f'Altruism: {prob:.1f}', bins=20)

		ax1.set_xlabel('Total Score')
		ax1.set_ylabel('Frequency')
		ax1.set_title('Total Score Distributions')
		ax1.legend()
		ax1.grid(True, alpha=0.3)

		# Plot 2: Player10 Score Distributions
		ax2 = axes[1]
		for prob in altruism_probs:
			scores = df[df['altruism_prob'] == prob]['player10_score']
			ax2.hist(scores, alpha=0.6, label=f'Altruism: {prob:.1f}', bins=20)

		ax2.set_xlabel('Player10 Score')
		ax2.set_ylabel('Frequency')
		ax2.set_title('Player10 Individual Score Distributions')
		ax2.legend()
		ax2.grid(True, alpha=0.3)

		plt.tight_layout()

		if save_path:
			plt.savefig(save_path, dpi=300, bbox_inches='tight')
			print(f'Distributions plot saved to: {save_path}')

		plt.show()

	def print_detailed_analysis(self):
		"""Print detailed analysis of the results."""
		if not self.results:
			print('No results loaded. Please load results first.')
			return

		df = self.create_dataframe()

		print('=== DETAILED ANALYSIS ===')
		print(f'Total simulations: {len(df)}')
		print(
			f'Unique configurations: {df.groupby(["altruism_prob", "tau_margin", "epsilon_fresh", "epsilon_mono"]).ngroups}'
		)

		# Overall statistics
		print('\n=== OVERALL STATISTICS ===')
		print(
			f'Total Score - Mean: {df["total_score"].mean():.2f}, Std: {df["total_score"].std():.2f}'
		)
		print(
			f'Player10 Score - Mean: {df["player10_score"].mean():.2f}, Std: {df["player10_score"].std():.2f}'
		)
		print(
			f'Conversation Length - Mean: {df["conversation_length"].mean():.1f}, Std: {df["conversation_length"].std():.1f}'
		)
		print(f'Early Termination Rate: {df["early_termination"].mean():.2f}')

		# Best configurations
		print('\n=== TOP 10 CONFIGURATIONS ===')
		top_configs = (
			df.groupby(['altruism_prob', 'tau_margin', 'epsilon_fresh', 'epsilon_mono'])
			.agg({'total_score': ['mean', 'std', 'count'], 'player10_score': 'mean'})
			.round(3)
		)

		top_configs.columns = ['total_mean', 'total_std', 'count', 'p10_mean']
		top_configs = top_configs.sort_values('total_mean', ascending=False).head(10)

		for i, (config, row) in enumerate(top_configs.iterrows(), 1):
			altruism, tau, fresh, mono = config
			print(
				f'{i:2d}. Altruism: {altruism:.1f}, Tau: {tau:.2f}, '
				f'Fresh: {fresh:.2f}, Mono: {mono:.2f} -> '
				f'Total: {row["total_mean"]:.2f}±{row["total_std"]:.2f}, '
				f'P10: {row["p10_mean"]:.2f}'
			)

		# Altruism analysis
		print('\n=== ALTRUISM ANALYSIS ===')
		altruism_stats = (
			df.groupby('altruism_prob')
			.agg(
				{
					'total_score': ['mean', 'std'],
					'player10_score': ['mean', 'std'],
					'conversation_length': 'mean',
					'early_termination': 'mean',
				}
			)
			.round(3)
		)

		for prob in sorted(df['altruism_prob'].unique()):
			stats = altruism_stats.loc[prob]
			print(
				f'Altruism {prob:.1f}: Total={stats[("total_score", "mean")]:.2f}±{stats[("total_score", "std")]:.2f}, '
				f'P10={stats[("player10_score", "mean")]:.2f}±{stats[("player10_score", "std")]:.2f}, '
				f'Length={stats[("conversation_length", "mean")]:.1f}, '
				f'EarlyTerm={stats[("early_termination", "mean")]:.2f}'
			)


def main():
	"""Main function for command-line usage."""
	import argparse

	parser = argparse.ArgumentParser(description='Analyze Monte Carlo simulation results')
	parser.add_argument('results_file', help='Path to results JSON file')
	parser.add_argument(
		'--plot',
		choices=['altruism', 'heatmap', 'distributions'],
		default='altruism',
		help='Type of plot to create',
	)
	parser.add_argument('--save', help='Save plot to file')
	parser.add_argument('--analysis', action='store_true', help='Print detailed analysis')

	args = parser.parse_args()

	# Load results
	analyzer = ResultsAnalyzer(args.results_file)

	# Print analysis
	if args.analysis:
		analyzer.print_detailed_analysis()

	# Create plots
	if args.plot == 'altruism':
		analyzer.plot_altruism_comparison(args.save)
	elif args.plot == 'heatmap':
		analyzer.plot_parameter_heatmap('altruism_prob', 'tau_margin', save_path=args.save)
	elif args.plot == 'distributions':
		analyzer.plot_score_distributions(args.save)


if __name__ == '__main__':
	main()
