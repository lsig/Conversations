"""
Batch runner script for Monte Carlo simulations.

This script provides easy-to-use functions for running different types of simulations
and analyzing the results.
"""

import argparse
import time
from pathlib import Path

from ..monte_carlo import MonteCarloSimulator, SimulationConfig


def run_altruism_comparison(num_simulations: int = 100):
    """
    Compare different altruism probabilities.
    
    Args:
        num_simulations: Number of simulations per configuration
    """
    print("=== ALTRUISM PROBABILITY COMPARISON ===")
    
    simulator = MonteCarloSimulator()
    
    # Test different altruism probabilities
    altruism_probs = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    
    print(f"Running {len(altruism_probs)} configurations with {num_simulations} simulations each...")
    print(f"Total simulations: {len(altruism_probs) * num_simulations}")
    
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        num_simulations=num_simulations,
        base_players={'p10': 10}
    )
    
    # Analyze and display results
    analysis = simulator.analyze_results()
    print_results_summary(analysis)
    
    # Save results
    filename = f"altruism_comparison_{int(time.time())}.json"
    simulator.save_results(filename)
    
    return simulator, analysis


def run_tau_sensitivity(num_simulations: int = 50):
    """
    Test sensitivity to tau margin parameter.
    
    Args:
        num_simulations: Number of simulations per configuration
    """
    print("=== TAU MARGIN SENSITIVITY ANALYSIS ===")
    
    simulator = MonteCarloSimulator()
    
    # Test different tau margins
    tau_margins = [0.01, 0.03, 0.05, 0.07, 0.10, 0.15]
    altruism_probs = [0.2, 0.5, 1.0]  # Test with different altruism levels
    
    print(f"Running {len(tau_margins) * len(altruism_probs)} configurations...")
    
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        tau_margins=tau_margins,
        num_simulations=num_simulations,
        base_players={'p10': 10}
    )
    
    analysis = simulator.analyze_results()
    print_results_summary(analysis)
    
    filename = f"tau_sensitivity_{int(time.time())}.json"
    simulator.save_results(filename)
    
    return simulator, analysis


def run_epsilon_sensitivity(num_simulations: int = 50):
    """
    Test sensitivity to epsilon parameters.
    
    Args:
        num_simulations: Number of simulations per configuration
    """
    print("=== EPSILON PARAMETERS SENSITIVITY ANALYSIS ===")
    
    simulator = MonteCarloSimulator()
    
    # Test different epsilon values
    epsilon_values = [0.01, 0.03, 0.05, 0.07, 0.10]
    altruism_probs = [0.5]  # Focus on moderate altruism
    
    print(f"Running {len(epsilon_values) * len(epsilon_values) * len(altruism_probs)} configurations...")
    
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        epsilon_fresh_values=epsilon_values,
        epsilon_mono_values=epsilon_values,
        num_simulations=num_simulations,
        base_players={'p10': 10}
    )
    
    analysis = simulator.analyze_results()
    print_results_summary(analysis)
    
    filename = f"epsilon_sensitivity_{int(time.time())}.json"
    simulator.save_results(filename)
    
    return simulator, analysis


def run_quick_test():
    """Run a quick test with minimal simulations."""
    print("=== QUICK TEST (10 simulations per config) ===")
    
    simulator = MonteCarloSimulator()
    
    altruism_probs = [0.0, 0.2, 0.5, 1.0]
    
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        num_simulations=10,
        base_players={'p10': 10}
    )
    
    analysis = simulator.analyze_results()
    print_results_summary(analysis)
    
    filename = f"quick_test_{int(time.time())}.json"
    simulator.save_results(filename)
    
    return simulator, analysis


def run_random_players_test(num_random_players: int = 2, num_simulations: int = 50):
    """
    Test Player10 against different numbers of random players.
    
    Args:
        num_random_players: Number of random players to add (2, 5, or 10)
        num_simulations: Number of simulations per configuration
    """
    print(f"=== RANDOM PLAYERS TEST ({num_random_players} random players) ===")
    
    simulator = MonteCarloSimulator()
    
    # Test different altruism probabilities against random players
    altruism_probs = [0.0, 0.2, 0.5, 1.0]
    
    # Create player configuration with Player10 + random players
    base_players = {'p10': 10, 'pr': num_random_players}
    
    print(f"Testing Player10 vs {num_random_players} random players...")
    print(f"Player configuration: {base_players}")
    
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        num_simulations=num_simulations,
        base_players=base_players
    )
    
    analysis = simulator.analyze_results()
    print_results_summary(analysis)
    
    filename = f"random_players_{num_random_players}_{int(time.time())}.json"
    simulator.save_results(filename)
    
    return simulator, analysis


def run_mixed_opponents_test(num_simulations: int = 50):
    """
    Test Player10 against a mix of different opponent types.
    
    Args:
        num_simulations: Number of simulations per configuration
    """
    print("=== MIXED OPPONENTS TEST ===")
    
    simulator = MonteCarloSimulator()
    
    # Test different altruism probabilities against mixed opponents
    altruism_probs = [0.0, 0.2, 0.5, 1.0]
    
    # Create mixed opponent configuration
    base_players = {
        'p10': 10,  # 10 Player10s
        'p0': 2,    # 2 Player0s (always pass)
        'p1': 2,    # 2 Player1s (strategic)
        'p2': 2,    # 2 Player2s (strategic)
        'pr': 4     # 4 Random players
    }
    
    print("Testing Player10 against mixed opponents...")
    print(f"Player configuration: {base_players}")
    
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        num_simulations=num_simulations,
        base_players=base_players
    )
    
    analysis = simulator.analyze_results()
    print_results_summary(analysis)
    
    filename = f"mixed_opponents_{int(time.time())}.json"
    simulator.save_results(filename)
    
    return simulator, analysis


def run_scalability_test():
    """
    Test Player10 performance with different numbers of random players (2, 5, 10).
    """
    print("=== SCALABILITY TEST (2, 5, 10 random players) ===")
    
    simulator = MonteCarloSimulator()
    all_results = []
    
    # Test against 2, 5, and 10 random players
    random_player_counts = [2, 5, 10]
    altruism_probs = [0.0, 0.5, 1.0]  # Original, mixed, full altruism
    
    for num_random in random_player_counts:
        print(f"\n--- Testing against {num_random} random players ---")
        
        base_players = {'p10': 10, 'pr': num_random}
        
        results = simulator.run_parameter_sweep(
            altruism_probs=altruism_probs,
            num_simulations=30,  # Fewer simulations for scalability test
            base_players=base_players
        )
        
        all_results.extend(results)
        
        # Quick analysis for this configuration
        temp_simulator = MonteCarloSimulator()
        temp_simulator.results = results
        analysis = temp_simulator.analyze_results()
        
        print(f"Results for {num_random} random players:")
        for i, config in enumerate(analysis['best_configurations'][:2], 1):
            altruism = config['config'][0]
            score = config['mean_score']
            print(f"  {i}. Altruism: {altruism:.1f} -> Score: {score:.2f}")
    
    # Overall analysis
    simulator.results = all_results
    overall_analysis = simulator.analyze_results()
    
    print(f"\n=== OVERALL SCALABILITY RESULTS ===")
    print(f"Total simulations: {len(all_results)}")
    print(f"Configurations tested: {len(random_player_counts) * len(altruism_probs)}")
    
    # Save all results
    filename = f"scalability_test_{int(time.time())}.json"
    simulator.save_results(filename)
    
    return simulator, overall_analysis


def print_results_summary(analysis):
    """Print a summary of the analysis results."""
    print(f"\n=== RESULTS SUMMARY ===")
    print(f"Total simulations: {analysis['total_simulations']}")
    print(f"Unique configurations: {analysis['unique_configurations']}")
    
    print(f"\n=== TOP 5 CONFIGURATIONS ===")
    for i, config in enumerate(analysis['best_configurations'], 1):
        altruism, tau, fresh, mono = config['config']
        print(f"{i}. Altruism: {altruism:.1f}, Tau: {tau:.2f}, "
              f"Fresh: {fresh:.2f}, Mono: {mono:.2f} -> "
              f"Score: {config['mean_score']:.2f}")
    
    # Show detailed results for top configurations
    print(f"\n=== DETAILED RESULTS FOR TOP 3 ===")
    for i, config in enumerate(analysis['best_configurations'][:3], 1):
        config_key = str(config['config'])
        if config_key in analysis['config_summaries']:
            summary = analysis['config_summaries'][config_key]
            print(f"\n{i}. Configuration: {config['config']}")
            print(f"   Total Score: {summary['total_score']['mean']:.2f} ± {summary['total_score']['std']:.2f}")
            print(f"   Player10 Score: {summary['player10_score']['mean']:.2f} ± {summary['player10_score']['std']:.2f}")
            print(f"   Avg Conversation Length: {summary['conversation_metrics']['avg_length']:.1f}")
            print(f"   Early Termination Rate: {summary['conversation_metrics']['early_termination_rate']:.2f}")


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Run Monte Carlo simulations for Player10')
    parser.add_argument('--test', choices=['altruism', 'tau', 'epsilon', 'quick', 'random2', 'random5', 'random10', 'mixed', 'scalability'], 
                       default='quick', help='Type of test to run')
    parser.add_argument('--simulations', type=int, default=50, 
                       help='Number of simulations per configuration')
    parser.add_argument('--output-dir', default='simulation_results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Set up output directory
    Path(args.output_dir).mkdir(exist_ok=True)
    
    print(f"Running {args.test} test with {args.simulations} simulations per configuration...")
    print(f"Results will be saved to: {args.output_dir}")
    print()
    
    start_time = time.time()
    
    if args.test == 'altruism':
        simulator, analysis = run_altruism_comparison(args.simulations)
    elif args.test == 'tau':
        simulator, analysis = run_tau_sensitivity(args.simulations)
    elif args.test == 'epsilon':
        simulator, analysis = run_epsilon_sensitivity(args.simulations)
    elif args.test == 'quick':
        simulator, analysis = run_quick_test()
    elif args.test == 'random2':
        simulator, analysis = run_random_players_test(2, args.simulations)
    elif args.test == 'random5':
        simulator, analysis = run_random_players_test(5, args.simulations)
    elif args.test == 'random10':
        simulator, analysis = run_random_players_test(10, args.simulations)
    elif args.test == 'mixed':
        simulator, analysis = run_mixed_opponents_test(args.simulations)
    elif args.test == 'scalability':
        simulator, analysis = run_scalability_test()
    
    end_time = time.time()
    print(f"\n=== SIMULATION COMPLETE ===")
    print(f"Total execution time: {end_time - start_time:.1f} seconds")
    print(f"Results saved in: {args.output_dir}")


if __name__ == "__main__":
    main()
