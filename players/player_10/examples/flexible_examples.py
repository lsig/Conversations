"""
Examples of using the flexible test framework.

This script demonstrates various ways to create and run custom tests.
"""

from ..sim.test_framework import (
    FlexibleTestRunner, TestBuilder, TestConfiguration,
    create_altruism_comparison_test, create_random_players_test,
    create_scalability_test, create_parameter_sweep_test,
    create_mixed_opponents_test
)


def example_basic_altruism_test():
    """Example: Basic altruism comparison test."""
    print("=== EXAMPLE 1: Basic Altruism Test ===")
    
    # Create test using builder
    config = (TestBuilder("basic_altruism", "Test different altruism probabilities")
              .altruism_range([0.0, 0.2, 0.5, 1.0])
              .player_configs([{'p10': 10}])
              .simulations(20)
              .conversation_length(50)
              .build())
    
    # Run test
    runner = FlexibleTestRunner()
    results = runner.run_test(config)
    
    print(f"Completed {len(results)} simulations")
    return results


def example_random_players_comparison():
    """Example: Compare performance against different numbers of random players."""
    print("\n=== EXAMPLE 2: Random Players Comparison ===")
    
    # Create multiple tests
    tests = [
        create_random_players_test(2),
        create_random_players_test(5),
        create_random_players_test(10)
    ]
    
    # Run all tests
    runner = FlexibleTestRunner()
    all_results = runner.run_multiple_tests(tests)
    
    # Print summary
    for test_name, results in all_results.items():
        print(f"{test_name}: {len(results)} simulations")
    
    return all_results


def example_custom_parameter_sweep():
    """Example: Custom parameter sweep with specific ranges."""
    print("\n=== EXAMPLE 3: Custom Parameter Sweep ===")
    
    config = (TestBuilder("custom_sweep", "Custom parameter sweep")
              .altruism_range([0.0, 0.5, 1.0])
              .tau_range([0.03, 0.05, 0.07])
              .epsilon_fresh_range([0.03, 0.05])
              .epsilon_mono_range([0.03, 0.05])
              .player_configs([
                  {'p10': 10},
                  {'p10': 10, 'pr': 2},
                  {'p10': 10, 'pr': 5}
              ])
              .simulations(15)
              .conversation_length(30)  # Shorter for faster testing
              .build())
    
    runner = FlexibleTestRunner()
    results = runner.run_test(config)
    
    print(f"Completed {len(results)} simulations")
    return results


def example_mixed_opponents_test():
    """Example: Test against mixed opponent types."""
    print("\n=== EXAMPLE 4: Mixed Opponents Test ===")
    
    config = (TestBuilder("mixed_test", "Test against mixed opponents")
              .altruism_range([0.0, 0.3, 0.7, 1.0])
              .player_configs([
                  {'p10': 10, 'p0': 2, 'p1': 2, 'pr': 4},  # Mixed opponents
                  {'p10': 10, 'pr': 8},  # All random opponents
                  {'p10': 10}  # No opponents (self-play)
              ])
              .simulations(25)
              .build())
    
    runner = FlexibleTestRunner()
    results = runner.run_test(config)
    
    print(f"Completed {len(results)} simulations")
    return results


def example_conversation_length_impact():
    """Example: Test impact of conversation length on performance."""
    print("\n=== EXAMPLE 5: Conversation Length Impact ===")
    
    # Create tests with different conversation lengths
    tests = []
    for length in [20, 50, 100]:
        config = (TestBuilder(f"length_{length}", f"Test with conversation length {length}")
                  .altruism_range([0.0, 0.5, 1.0])
                  .player_configs([{'p10': 10}])
                  .simulations(20)
                  .conversation_length(length)
                  .build())
        tests.append(config)
    
    runner = FlexibleTestRunner()
    all_results = runner.run_multiple_tests(tests)
    
    # Print summary
    for test_name, results in all_results.items():
        print(f"{test_name}: {len(results)} simulations")
    
    return all_results


def example_quick_validation():
    """Example: Quick validation test with minimal simulations."""
    print("\n=== EXAMPLE 6: Quick Validation ===")
    
    config = (TestBuilder("quick_validation", "Quick validation test")
              .altruism_range([0.0, 1.0])  # Just original vs full altruism
              .player_configs([
                  {'p10': 10},
                  {'p10': 10, 'pr': 2}
              ])
              .simulations(5)  # Very few simulations
              .conversation_length(20)  # Short conversations
              .build())
    
    runner = FlexibleTestRunner()
    results = runner.run_test(config)
    
    print(f"Completed {len(results)} simulations")
    return results


def example_comprehensive_study():
    """Example: Comprehensive study with multiple test types."""
    print("\n=== EXAMPLE 7: Comprehensive Study ===")
    
    # Create a comprehensive set of tests
    tests = [
        create_altruism_comparison_test(),
        create_scalability_test(),
        create_mixed_opponents_test()
    ]
    
    # Add custom tests
    custom_tests = [
        (TestBuilder("high_altruism", "Test high altruism probabilities")
         .altruism_range([0.8, 0.9, 1.0])
         .player_configs([{'p10': 10}])
         .simulations(30)
         .build()),
        
        (TestBuilder("tau_sensitivity", "Test tau sensitivity")
         .altruism_range([0.5])  # Fixed altruism
         .tau_range([0.01, 0.03, 0.05, 0.07, 0.10, 0.15])
         .player_configs([{'p10': 10}])
         .simulations(25)
         .build())
    ]
    
    all_tests = tests + custom_tests
    
    # Run all tests
    runner = FlexibleTestRunner()
    all_results = runner.run_multiple_tests(all_tests)
    
    # Print comprehensive summary
    print(f"\n=== COMPREHENSIVE STUDY COMPLETE ===")
    total_simulations = sum(len(results) for results in all_results.values())
    print(f"Total simulations: {total_simulations}")
    print(f"Tests completed: {len(all_results)}")
    
    for test_name, results in all_results.items():
        print(f"  {test_name}: {len(results)} simulations")
    
    return all_results


def main():
    """Run all examples."""
    print("Flexible Test Framework Examples")
    print("=" * 50)
    
    # Run examples (comment out any you don't want to run)
    example_basic_altruism_test()
    example_random_players_comparison()
    example_custom_parameter_sweep()
    example_mixed_opponents_test()
    example_conversation_length_impact()
    example_quick_validation()
    # example_comprehensive_study()  # Uncomment for comprehensive study
    
    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    main()
