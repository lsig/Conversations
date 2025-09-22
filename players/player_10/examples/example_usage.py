"""
Example usage of the Monte Carlo simulation framework.

This script demonstrates how to run simulations and analyze results
for different Player10 configurations.
"""

from ..analysis.analyze_results import ResultsAnalyzer
from ..sim.monte_carlo import MonteCarloSimulator, SimulationConfig


def example_quick_test():
	"""Run a quick test with a few simulations."""
	print('=== QUICK TEST EXAMPLE ===')

	# Create simulator
	simulator = MonteCarloSimulator('example_results')

	# Test different altruism probabilities
	altruism_probs = [0.0, 0.2, 0.5, 1.0]

	print('Running quick test...')
	results = simulator.run_parameter_sweep(
		altruism_probs=altruism_probs,
		num_simulations=10,  # Small number for quick test
		base_players={'p10': 10},
	)

	# Analyze results
	analysis = simulator.analyze_results()

	# Print summary
	print(f'\nResults: {len(results)} simulations completed')
	print(f'Best configuration: {analysis["best_configurations"][0]}')

	# Save results
	filename = simulator.save_results('quick_test_example.json')
	print(f'Results saved to: {filename}')

	return simulator, analysis


def example_detailed_analysis():
	"""Run a more detailed analysis with visualizations."""
	print('=== DETAILED ANALYSIS EXAMPLE ===')

	# Run simulations
	simulator = MonteCarloSimulator('detailed_results')

	altruism_probs = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

	print('Running detailed analysis...')
	simulator.run_parameter_sweep(
		altruism_probs=altruism_probs, num_simulations=50, base_players={'p10': 10}
	)

	# Save results
	simulator.save_results('detailed_analysis.json')

	# Analyze with visualizations
	analyzer = ResultsAnalyzer()
	analyzer.load_results('detailed_analysis.json')

	# Print detailed analysis
	analyzer.print_detailed_analysis()

	# Create plots (uncomment if you have matplotlib/seaborn installed)
	# analyzer.plot_altruism_comparison("altruism_comparison.png")
	# analyzer.plot_score_distributions("score_distributions.png")

	return simulator, analyzer


def example_custom_configuration():
	"""Example of running simulations with custom configuration."""
	print('=== CUSTOM CONFIGURATION EXAMPLE ===')

	simulator = MonteCarloSimulator('custom_results')

	# Create custom configuration
	config = SimulationConfig(
		altruism_prob=0.3,
		tau_margin=0.07,
		epsilon_fresh=0.03,
		epsilon_mono=0.08,
		seed=12345,
		players={'p10': 10, 'pr': 2},
	)

	print('Running single simulation with custom config...')
	result = simulator.run_single_simulation(config)

	print('Simulation completed:')
	print(f'  Total Score: {result.total_score:.2f}')
	print(f'  Player10 Score: {result.player_scores.get("Player10", 0):.2f}')
	print(f'  Conversation Length: {result.conversation_length}')
	print(f'  Early Termination: {result.early_termination}')
	print(f'  Execution Time: {result.execution_time:.2f}s')

	return result


def main():
	"""Run all examples."""
	print('Monte Carlo Simulation Examples for Player10')
	print('=' * 50)

	# Example 1: Quick test
	print('\n1. Quick Test')
	simulator1, analysis1 = example_quick_test()

	# Example 2: Custom configuration
	print('\n2. Custom Configuration')
	example_custom_configuration()

	# Example 3: Detailed analysis (uncomment to run)
	# print("\n3. Detailed Analysis")
	# simulator2, analyzer = example_detailed_analysis()

	print('\n' + '=' * 50)
	print("Examples completed! Check the 'simulation_results' directory for saved results.")


if __name__ == '__main__':
	main()
