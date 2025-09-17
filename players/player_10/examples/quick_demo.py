"""
Quick demo of the flexible test framework.

This demonstrates the key features of the new framework.
"""

from ..sim.test_framework import TestBuilder, FlexibleTestRunner, create_altruism_comparison_test


def demo_basic_usage():
    """Demonstrate basic usage of the flexible framework."""
    print("=== FLEXIBLE FRAMEWORK DEMO ===")
    
    # Method 1: Use predefined test
    print("\n1. Using predefined test:")
    config = create_altruism_comparison_test()
    print(f"   Test: {config.name}")
    print(f"   Altruism values: {config.altruism_probs.values}")
    print(f"   Player configs: {config.player_configs}")
    print(f"   Simulations: {config.num_simulations}")
    print(f"   Conversation length: {config.conversation_length}")
    
    # Method 2: Create custom test with builder
    print("\n2. Creating custom test with builder:")
    custom_config = (TestBuilder("demo_test", "Demo test with custom parameters")
                     .altruism_range([0.0, 0.5, 1.0])
                     .player_configs([{'p10': 10}])
                     .simulations(5)  # Very small for demo
                     .conversation_length(20)  # Short for demo
                     .build())
    
    print(f"   Test: {custom_config.name}")
    print(f"   Description: {custom_config.description}")
    print(f"   Altruism values: {custom_config.altruism_probs.values}")
    print(f"   Player configs: {custom_config.player_configs}")
    print(f"   Simulations: {custom_config.num_simulations}")
    print(f"   Conversation length: {custom_config.conversation_length}")
    
    # Method 3: Run the test
    print("\n3. Running the test:")
    runner = FlexibleTestRunner()
    
    # Note: This would run actual simulations, but we'll just show the setup
    print("   Test configuration ready to run!")
    print("   Use runner.run_test(custom_config) to execute")
    
    return custom_config


def demo_command_line_equivalents():
    """Show command line equivalents for the demo."""
    print("\n=== COMMAND LINE EQUIVALENTS ===")
    
    print("\n1. Run predefined altruism test:")
    print("   python -m players.player_10.flexible_runner --predefined altruism")
    
    print("\n2. Run custom test:")
    print("   python -m players.player_10.flexible_runner --name 'demo_test' --altruism 0.0 0.5 1.0 --simulations 5 --conversation-length 20")
    
    print("\n3. Test against random players:")
    print("   python -m players.player_10.flexible_runner --name 'random_test' --players '{\"p10\": 10, \"pr\": 5}' --altruism 0.0 0.5 1.0")
    
    print("\n4. Parameter sweep:")
    print("   python -m players.player_10.flexible_runner --name 'sweep' --altruism 0.0 0.5 1.0 --tau 0.03 0.05 0.07 --simulations 20")


def demo_advanced_features():
    """Demonstrate advanced features."""
    print("\n=== ADVANCED FEATURES ===")
    
    # Multiple player configurations
    print("\n1. Multiple player configurations:")
    config = (TestBuilder("multi_player_test")
              .altruism_range([0.0, 1.0])
              .player_configs([
                  {'p10': 10},  # Self-play
                  {'p10': 10, 'pr': 2},  # vs 2 random
                  {'p10': 10, 'pr': 5},  # vs 5 random
                  {'p10': 10, 'p0': 2, 'p1': 2, 'pr': 4}  # Mixed opponents
              ])
              .simulations(10)
              .build())
    
    print(f"   Player configurations: {config.player_configs}")
    print(f"   Total combinations: {len(config.altruism_probs.values) * len(config.player_configs)}")
    
    # Parameter sweep
    print("\n2. Parameter sweep:")
    sweep_config = (TestBuilder("parameter_sweep")
                    .altruism_range([0.0, 0.5, 1.0])
                    .tau_range([0.03, 0.05, 0.07])
                    .epsilon_fresh_range([0.03, 0.05])
                    .player_configs([{'p10': 10}])
                    .simulations(5)
                    .build())
    
    total_combinations = (len(sweep_config.altruism_probs.values) * 
                         len(sweep_config.tau_margins.values) * 
                         len(sweep_config.epsilon_fresh_values.values))
    print(f"   Parameter combinations: {total_combinations}")
    print(f"   Total simulations: {total_combinations * sweep_config.num_simulations}")


if __name__ == "__main__":
    demo_basic_usage()
    demo_command_line_equivalents()
    demo_advanced_features()
    
    print("\n" + "=" * 50)
    print("Demo completed! The flexible framework is ready to use.")
    print("Check FLEXIBLE_FRAMEWORK_README.md for complete documentation.")
