"""
Demo script showing how to use the Monte Carlo simulation framework.

This script runs a simple demonstration of the framework capabilities.
"""

def run_demo():
    """Run a simple demonstration of the Monte Carlo framework."""
    print("=== Player10 Monte Carlo Simulation Demo ===")
    print()
    
    # Import the framework
    from ..monte_carlo import MonteCarloSimulator, SimulationConfig
    
    print("1. Creating simulator...")
    simulator = MonteCarloSimulator("demo_results")
    
    print("2. Running quick test with 3 configurations...")
    
    # Test different altruism probabilities
    altruism_probs = [0.0, 0.5, 1.0]  # Original, mixed, full altruism
    
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        num_simulations=5,  # Very small for demo
        base_players={'p10': 10}
    )
    
    print(f"   Completed {len(results)} simulations")
    
    print("3. Analyzing results...")
    analysis = simulator.analyze_results()
    
    print("4. Results Summary:")
    print(f"   Total simulations: {analysis['total_simulations']}")
    print(f"   Unique configurations: {analysis['unique_configurations']}")
    
    print("\n5. Top Configurations:")
    for i, config in enumerate(analysis['best_configurations'][:3], 1):
        altruism = config['config'][0]
        score = config['mean_score']
        print(f"   {i}. Altruism: {altruism:.1f} -> Score: {score:.2f}")
    
    print("\n6. Saving results...")
    filename = simulator.save_results("demo_results.json")
    print(f"   Results saved to: {filename}")
    
    print("\n=== Demo Complete ===")
    print("You can now:")
    print("- Run more simulations with different parameters")
    print("- Analyze results with visualizations")
    print("- Find optimal configurations for your use case")
    
    return simulator, analysis


if __name__ == "__main__":
    run_demo()
