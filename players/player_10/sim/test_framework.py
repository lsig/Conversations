"""
Flexible test configuration framework for Player10 Monte Carlo simulations.

This module provides a flexible way to define and run custom test configurations
without being limited to predefined test types.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable

from .monte_carlo import MonteCarloSimulator, SimulationConfig, SimulationResult


@dataclass
class ParameterRange:
    """Defines a range of values for a parameter."""
    values: List[Any]
    name: str
    description: str = ""


@dataclass
class TestConfiguration:
    """Configuration for a custom test."""
    name: str
    description: str = ""
    
    # Parameter ranges to test
    altruism_probs: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[0.0, 0.2, 0.5, 1.0],
        name="altruism_prob",
        description="Altruism probability"
    ))
    tau_margins: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[0.05],
        name="tau_margin", 
        description="Tau margin"
    ))
    epsilon_fresh_values: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[0.05],
        name="epsilon_fresh",
        description="Epsilon fresh"
    ))
    epsilon_mono_values: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[0.05],
        name="epsilon_mono",
        description="Epsilon mono"
    ))
    
    # Player configurations to test
    player_configs: List[Dict[str, int]] = field(default_factory=lambda: [{'p10': 10}])
    
    # Simulation parameters
    num_simulations: int = 50
    conversation_length: int = 50
    subjects: int = 20
    memory_size: int = 10
    base_seed: int = 42
    
    # Output settings
    output_dir: str = "simulation_results"
    save_results: bool = True
    print_progress: bool = True
    # Extended knobs (optional ranges)
    min_samples_values: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[3], name="min_samples_pid", description="Min samples per player for trusted mean"
    ))
    ewma_alpha_values: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[0.10], name="ewma_alpha", description="EWMA alpha"
    ))
    importance_weights: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[1.0], name="importance_weight", description="Importance weight"
    ))
    coherence_weights: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[1.0], name="coherence_weight", description="Coherence weight"
    ))
    freshness_weights: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[1.0], name="freshness_weight", description="Freshness weight"
    ))
    monotony_weights: ParameterRange = field(default_factory=lambda: ParameterRange(
        values=[1.0], name="monotony_weight", description="Monotony weight"
    ))


class TestBuilder:
    """Builder class for creating custom test configurations."""
    
    def __init__(self, name: str, description: str = ""):
        self.config = TestConfiguration(name=name, description=description)
    
    def altruism_range(self, values: List[float]) -> 'TestBuilder':
        """Set altruism probability range."""
        self.config.altruism_probs = ParameterRange(
            values=values, name="altruism_prob", description="Altruism probability"
        )
        return self
    
    def tau_range(self, values: List[float]) -> 'TestBuilder':
        """Set tau margin range."""
        self.config.tau_margins = ParameterRange(
            values=values, name="tau_margin", description="Tau margin"
        )
        return self
    
    def epsilon_fresh_range(self, values: List[float]) -> 'TestBuilder':
        """Set epsilon fresh range."""
        self.config.epsilon_fresh_values = ParameterRange(
            values=values, name="epsilon_fresh", description="Epsilon fresh"
        )
        return self
    
    def epsilon_mono_range(self, values: List[float]) -> 'TestBuilder':
        """Set epsilon mono range."""
        self.config.epsilon_mono_values = ParameterRange(
            values=values, name="epsilon_mono", description="Epsilon mono"
        )
        return self
    
    def player_configs(self, configs: List[Dict[str, int]]) -> 'TestBuilder':
        """Set player configurations to test."""
        self.config.player_configs = configs
        return self
    
    def add_player_config(self, config: Dict[str, int]) -> 'TestBuilder':
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
    def min_samples_range(self, values: List[int]) -> 'TestBuilder':
        self.config.min_samples_values = ParameterRange(values=values, name="min_samples_pid", description="Min samples per player")
        return self

    def ewma_alpha_range(self, values: List[float]) -> 'TestBuilder':
        self.config.ewma_alpha_values = ParameterRange(values=values, name="ewma_alpha", description="EWMA alpha")
        return self

    def importance_weight_range(self, values: List[float]) -> 'TestBuilder':
        self.config.importance_weights = ParameterRange(values=values, name="importance_weight", description="Importance weight")
        return self

    def coherence_weight_range(self, values: List[float]) -> 'TestBuilder':
        self.config.coherence_weights = ParameterRange(values=values, name="coherence_weight", description="Coherence weight")
        return self

    def freshness_weight_range(self, values: List[float]) -> 'TestBuilder':
        self.config.freshness_weights = ParameterRange(values=values, name="freshness_weight", description="Freshness weight")
        return self

    def monotony_weight_range(self, values: List[float]) -> 'TestBuilder':
        self.config.monotony_weights = ParameterRange(values=values, name="monotony_weight", description="Monotony weight")
        return self
    
    def output_dir(self, directory: str) -> 'TestBuilder':
        """Set output directory."""
        self.config.output_dir = directory
        return self
    
    def build(self) -> TestConfiguration:
        """Build the test configuration."""
        return self.config


class FlexibleTestRunner:
    """Flexible test runner that can execute any test configuration."""
    
    def __init__(self, output_dir: str = "simulation_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.simulator = MonteCarloSimulator(str(self.output_dir))
        self.results: List[SimulationResult] = []
    
    def run_test(self, config: TestConfiguration) -> List[SimulationResult]:
        """
        Run a test configuration.
        
        Args:
            config: Test configuration to run
            
        Returns:
            List of simulation results
        """
        print(f"=== RUNNING TEST: {config.name} ===")
        if config.description:
            print(f"Description: {config.description}")
        
        print(f"Parameter combinations: {self._count_combinations(config)}")
        print(f"Total simulations: {self._count_combinations(config) * config.num_simulations}")
        print()
        
        all_results = []
        combination_count = 0
        total_combinations = self._count_combinations(config)
        total_simulations = total_combinations * config.num_simulations
        pbar = None
        if config.print_progress and total_simulations > 0:
            try:
                from tqdm.auto import tqdm  # type: ignore
                pbar = tqdm(total=total_simulations, desc="Simulations", leave=False)
            except Exception:
                pbar = None
        
        # Generate all parameter combinations
        for param_combo in self._generate_parameter_combinations(config):
            for player_config in config.player_configs:
                combination_count += 1
                
                if config.print_progress:
                    print(f"Running combination {combination_count}/{total_combinations}: "
                          f"params={param_combo}, players={player_config}")
                
                # Create simulation config
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
                    min_samples_pid=param_combo.get('min_samples_pid', config.min_samples_values.values[0]),
                    ewma_alpha=param_combo.get('ewma_alpha', config.ewma_alpha_values.values[0]),
                    importance_weight=param_combo.get('importance_weight', config.importance_weights.values[0]),
                    coherence_weight=param_combo.get('coherence_weight', config.coherence_weights.values[0]),
                    freshness_weight=param_combo.get('freshness_weight', config.freshness_weights.values[0]),
                    monotony_weight=param_combo.get('monotony_weight', config.monotony_weights.values[0])
                )
                
                # Run simulations for this combination
                for sim_idx in range(config.num_simulations):
                    sim_config.seed = config.base_seed + combination_count * config.num_simulations + sim_idx
                    result = self.simulator.run_single_simulation(sim_config)
                    all_results.append(result)
                    if pbar is not None:
                        pbar.update(1)

        if pbar is not None:
            pbar.close()
        
        self.results = all_results
        
        if config.save_results:
            filename = f"{config.name}_{int(time.time())}.json"
            self.simulator.results = all_results
            self.simulator.save_results(filename)
            print(f"Results saved to: {filename}")
        
        print(f"Test completed: {len(all_results)} simulations")
        return all_results
    
    def run_multiple_tests(self, configs: List[TestConfiguration]) -> Dict[str, List[SimulationResult]]:
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
        """Count total parameter combinations."""
        param_count = (len(config.altruism_probs.values) * 
                      len(config.tau_margins.values) * 
                      len(config.epsilon_fresh_values.values) * 
                      len(config.epsilon_mono_values.values))
        return param_count * len(config.player_configs)
    
    def _generate_parameter_combinations(self, config: TestConfiguration) -> List[Dict[str, Any]]:
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
                                                combinations.append({
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
                                                })
        
        return combinations


# Predefined test configurations for common use cases
def create_altruism_comparison_test() -> TestConfiguration:
    """Create a test comparing different altruism probabilities."""
    return (TestBuilder("altruism_comparison", "Compare different altruism probabilities")
            .altruism_range([0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0])
            .player_configs([{'p10': 10}])
            .simulations(50)
            .build())


def create_random_players_test(num_random: int) -> TestConfiguration:
    """Create a test against random players."""
    return (TestBuilder(f"random_{num_random}", f"Test against {num_random} random players")
            .altruism_range([0.0, 0.2, 0.5, 1.0])
            .player_configs([{'p10': 10, 'pr': num_random}])
            .simulations(50)
            .build())


def create_scalability_test() -> TestConfiguration:
    """Create a scalability test with different numbers of random players."""
    return (TestBuilder("scalability", "Test scalability with different random player counts")
            .altruism_range([0.0, 0.5, 1.0])
            .player_configs([
                {'p10': 10, 'pr': 2},
                {'p10': 10, 'pr': 5},
                {'p10': 10, 'pr': 10}
            ])
            .simulations(30)
            .build())


def create_parameter_sweep_test() -> TestConfiguration:
    """Create a comprehensive parameter sweep test."""
    return (TestBuilder("parameter_sweep", "Comprehensive parameter sweep")
            .altruism_range([0.0, 0.2, 0.5, 1.0])
            .tau_range([0.01, 0.03, 0.05, 0.07, 0.10])
            .epsilon_fresh_range([0.01, 0.03, 0.05, 0.07])
            .epsilon_mono_range([0.01, 0.03, 0.05, 0.07])
            .player_configs([{'p10': 10}])
            .simulations(20)  # Fewer simulations due to large parameter space
            .build())


def create_mixed_opponents_test() -> TestConfiguration:
    """Create a test against mixed opponent types."""
    return (TestBuilder("mixed_opponents", "Test against mixed opponent types")
            .altruism_range([0.0, 0.2, 0.5, 1.0])
            .player_configs([{
                'p10': 10,
                'p0': 2,
                'p1': 2,
                'p2': 2,
                'pr': 4
            }])
            .simulations(50)
            .build())


# Example usage and demo functions
def run_example_tests():
    """Run example tests to demonstrate the framework."""
    runner = FlexibleTestRunner()
    
    # Create some example tests
    tests = [
        create_altruism_comparison_test(),
        create_random_players_test(5),
        create_scalability_test()
    ]
    
    # Run all tests
    results = runner.run_multiple_tests(tests)
    
    # Print summary
    print("\n=== TEST SUMMARY ===")
    for test_name, test_results in results.items():
        print(f"{test_name}: {len(test_results)} simulations")
    
    return results


if __name__ == "__main__":
    run_example_tests()
