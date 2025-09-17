"""
Monte Carlo simulation framework for testing Player10 strategies.

This module provides tools to run multiple simulations with different parameterizations
and analyze the results to find optimal strategy configurations.
"""

import json
import random
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Any

from core.engine import Engine
from models.cli import Settings
from models.player import Player

from ..agent.config import (
    ALTRUISM_USE_PROB,
    TAU_MARGIN,
    EPSILON_FRESH,
    EPSILON_MONO,
    MIN_SAMPLES_PID,
    EWMA_ALPHA,
    IMPORTANCE_WEIGHT,
    COHERENCE_WEIGHT,
    FRESHNESS_WEIGHT,
    MONOTONY_WEIGHT,
)
from ..agent.player import Player10


@dataclass
class SimulationConfig:
    """Configuration for a single simulation run."""
    altruism_prob: float
    tau_margin: float
    epsilon_fresh: float
    epsilon_mono: float
    seed: int
    players: Dict[str, int]
    subjects: int = 20
    memory_size: int = 10
    conversation_length: int = 50
    # Extended config knobs (defaults pulled from agent.config)
    min_samples_pid: int = MIN_SAMPLES_PID
    ewma_alpha: float = EWMA_ALPHA
    importance_weight: float = IMPORTANCE_WEIGHT
    coherence_weight: float = COHERENCE_WEIGHT
    freshness_weight: float = FRESHNESS_WEIGHT
    monotony_weight: float = MONOTONY_WEIGHT


@dataclass
class SimulationResult:
    """Results from a single simulation run."""
    config: SimulationConfig
    total_score: float
    player_scores: Dict[str, float]
    player_contributions: Dict[str, int]
    conversation_length: int
    early_termination: bool
    pause_count: int
    unique_items_used: int
    execution_time: float


class MonteCarloSimulator:
    """Monte Carlo simulator for testing Player10 strategies."""
    
    def __init__(self, output_dir: str = "simulation_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[SimulationResult] = []
    
    def run_single_simulation(self, config: SimulationConfig) -> SimulationResult:
        """
        Run a single simulation with the given configuration.
        
        Args:
            config: Configuration for the simulation
            
        Returns:
            Results from the simulation
        """
        start_time = time.time()
        
        # Set random seed for reproducibility
        random.seed(config.seed)
        
        # Temporarily update Player10 config
        self._update_player10_config(config)
        
        try:
            # Create players
            players = self._create_players(config.players)
            
            # Create engine
            engine = Engine(
                players=players,
                player_count=sum(config.players.values()),
                subjects=config.subjects,
                memory_size=config.memory_size,
                conversation_length=config.conversation_length,
                seed=config.seed,
            )
            
            # Run simulation
            simulation_results = engine.run(players)
            
            # Extract results
            result = self._extract_results(config, simulation_results, time.time() - start_time)
            
            return result
            
        finally:
            # Reset config to original values
            self._reset_player10_config()
    
    def run_parameter_sweep(
        self,
        altruism_probs: List[float],
        tau_margins: List[float] = None,
        epsilon_fresh_values: List[float] = None,
        epsilon_mono_values: List[float] = None,
        num_simulations: int = 100,
        base_players: Dict[str, int] = None,
        base_seed: int = 42
    ) -> List[SimulationResult]:
        """
        Run a parameter sweep across different configurations.
        
        Args:
            altruism_probs: List of altruism probabilities to test
            tau_margins: List of tau margin values (default: [0.05])
            epsilon_fresh_values: List of epsilon fresh values (default: [0.05])
            epsilon_mono_values: List of epsilon mono values (default: [0.05])
            num_simulations: Number of simulations per configuration
            base_players: Base player configuration
            base_seed: Base seed for random number generation
            
        Returns:
            List of all simulation results
        """
        if tau_margins is None:
            tau_margins = [0.05]
        if epsilon_fresh_values is None:
            epsilon_fresh_values = [0.05]
        if epsilon_mono_values is None:
            epsilon_mono_values = [0.05]
        if base_players is None:
            base_players = {'p10': 1, 'p0': 1, 'p1': 1, 'p2': 1}
        
        all_results = []
        total_configs = len(altruism_probs) * len(tau_margins) * len(epsilon_fresh_values) * len(epsilon_mono_values)
        total_sims = total_configs * num_simulations
        
        print(f"Running {total_sims} simulations across {total_configs} configurations...")
        
        sim_count = 0
        for altruism_prob in altruism_probs:
            for tau_margin in tau_margins:
                for epsilon_fresh in epsilon_fresh_values:
                    for epsilon_mono in epsilon_mono_values:
                        config = SimulationConfig(
                            altruism_prob=altruism_prob,
                            tau_margin=tau_margin,
                            epsilon_fresh=epsilon_fresh,
                            epsilon_mono=epsilon_mono,
                            seed=base_seed,
                            players=base_players.copy()
                        )
                        
                        print(f"Testing config: altruism={altruism_prob}, tau={tau_margin}, "
                              f"fresh={epsilon_fresh}, mono={epsilon_mono}")
                        
                        for sim_idx in range(num_simulations):
                            config.seed = base_seed + sim_count
                            result = self.run_single_simulation(config)
                            all_results.append(result)
                            sim_count += 1
                            
                            if sim_count % 10 == 0:
                                print(f"Completed {sim_count}/{total_sims} simulations")
        
        self.results = all_results
        return all_results
    
    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze the simulation results and return summary statistics.
        
        Returns:
            Dictionary containing analysis results
        """
        if not self.results:
            return {}
        
        # Group results by configuration
        config_groups = defaultdict(list)
        for result in self.results:
            key = (result.config.altruism_prob, result.config.tau_margin, 
                   result.config.epsilon_fresh, result.config.epsilon_mono)
            config_groups[key].append(result)
        
        analysis = {
            'total_simulations': len(self.results),
            'unique_configurations': len(config_groups),
            'config_summaries': {},
            'best_configurations': []
        }
        
        # Analyze each configuration
        config_scores = []
        for config_key, results in config_groups.items():
            scores = [r.total_score for r in results]
            player10_scores = [r.player_scores.get('Player10', 0) for r in results]
            
            summary = {
                'config': {
                    'altruism_prob': config_key[0],
                    'tau_margin': config_key[1],
                    'epsilon_fresh': config_key[2],
                    'epsilon_mono': config_key[3]
                },
                'total_score': {
                    'mean': sum(scores) / len(scores),
                    'std': self._calculate_std(scores),
                    'min': min(scores),
                    'max': max(scores)
                },
                'player10_score': {
                    'mean': sum(player10_scores) / len(player10_scores),
                    'std': self._calculate_std(player10_scores),
                    'min': min(player10_scores),
                    'max': max(player10_scores)
                },
                'conversation_metrics': {
                    'avg_length': sum(r.conversation_length for r in results) / len(results),
                    'early_termination_rate': sum(r.early_termination for r in results) / len(results),
                    'avg_pause_count': sum(r.pause_count for r in results) / len(results),
                    'avg_unique_items': sum(r.unique_items_used for r in results) / len(results)
                }
            }
            
            analysis['config_summaries'][str(config_key)] = summary
            config_scores.append((config_key, summary['total_score']['mean']))
        
        # Find best configurations
        config_scores.sort(key=lambda x: x[1], reverse=True)
        analysis['best_configurations'] = [
            {'config': config_key, 'mean_score': score}
            for config_key, score in config_scores[:5]
        ]
        
        return analysis
    
    def save_results(self, filename: str = None) -> str:
        """
        Save simulation results to a JSON file.
        
        Args:
            filename: Optional filename (default: timestamp-based)
            
        Returns:
            Path to the saved file
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"simulation_results_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        # Convert results to serializable format
        serializable_results = []
        for result in self.results:
            serializable_results.append({
                'config': asdict(result.config),
                'total_score': result.total_score,
                'player_scores': result.player_scores,
                'player_contributions': result.player_contributions,
                'conversation_length': result.conversation_length,
                'early_termination': result.early_termination,
                'pause_count': result.pause_count,
                'unique_items_used': result.unique_items_used,
                'execution_time': result.execution_time
            })
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        print(f"Results saved to: {filepath}")
        return str(filepath)
    
    def load_results(self, filename: str) -> List[SimulationResult]:
        """
        Load simulation results from a JSON file.
        
        Args:
            filename: Name of the file to load
            
        Returns:
            List of simulation results
        """
        filepath = self.output_dir / filename
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        results = []
        for item in data:
            config = SimulationConfig(**item['config'])
            result = SimulationResult(
                config=config,
                total_score=item['total_score'],
                player_scores=item['player_scores'],
                player_contributions=item['player_contributions'],
                conversation_length=item['conversation_length'],
                early_termination=item['early_termination'],
                pause_count=item['pause_count'],
                unique_items_used=item['unique_items_used'],
                execution_time=item['execution_time']
            )
            results.append(result)
        
        self.results = results
        return results
    
    def _create_players(self, player_config: Dict[str, int]) -> List[type[Player]]:
        """Create player instances based on configuration."""
        from players.player_0.player import Player0
        from players.player_1.player import Player1
        from players.player_2.player import Player2
        from players.random_player import RandomPlayer
        
        players = []
        player_classes = {
            'p0': Player0,
            'p1': Player1,
            'p2': Player2,
            'p10': Player10,
            'pr': RandomPlayer,
        }
        
        for player_type, count in player_config.items():
            if player_type in player_classes:
                players.extend([player_classes[player_type]] * count)
        
        return players
    
    def _update_player10_config(self, config: SimulationConfig):
        """Temporarily update Player10 configuration."""
        import players.player_10.agent.config as config_module
        config_module.ALTRUISM_USE_PROB = config.altruism_prob
        config_module.TAU_MARGIN = config.tau_margin
        config_module.EPSILON_FRESH = config.epsilon_fresh
        config_module.EPSILON_MONO = config.epsilon_mono
        config_module.MIN_SAMPLES_PID = config.min_samples_pid
        config_module.EWMA_ALPHA = config.ewma_alpha
        config_module.IMPORTANCE_WEIGHT = config.importance_weight
        config_module.COHERENCE_WEIGHT = config.coherence_weight
        config_module.FRESHNESS_WEIGHT = config.freshness_weight
        config_module.MONOTONY_WEIGHT = config.monotony_weight
    
    def _reset_player10_config(self):
        """Reset Player10 configuration to original values."""
        import players.player_10.agent.config as config_module
        # Note: we do not have original snapshot; leave as-is after run to avoid conflicting concurrent tests.
        # For isolation, each run sets values explicitly before it starts.
    
    def _extract_results(self, config: SimulationConfig, simulation_results: Any, execution_time: float) -> SimulationResult:
        """Extract results from engine simulation output."""
        # Extract data from simulation results dictionary
        history = simulation_results.get('history', [])
        score_breakdown = simulation_results.get('score_breakdown', {})
        scores = simulation_results.get('scores', {})
        
        # Calculate total score from score breakdown
        total_score = sum(score_breakdown.values()) if score_breakdown else 0.0
        
        # Calculate player scores (individual contributions)
        player_scores = {}
        # For now, use a simple approach - we'll improve this later
        if 'individual_scores' in scores:
            for player_id_str, score in scores['individual_scores'].items():
                player_scores[f"Player_{player_id_str[:8]}"] = score
        else:
            # Fallback: distribute total score equally among players
            num_players = len([item for item in history if item is not None and hasattr(item, 'player_id')])
            if num_players > 0:
                avg_score = total_score / num_players
                player_scores["Player10"] = avg_score
        
        # Calculate player contributions
        player_contributions = {}
        # Count contributions by player
        player_contribution_counts = {}
        for item in history:
            if item is not None and hasattr(item, 'player_id'):
                player_id = str(item.player_id)
                player_contribution_counts[player_id] = player_contribution_counts.get(player_id, 0) + 1
        
        for player_id, count in player_contribution_counts.items():
            player_contributions[f"Player_{player_id[:8]}"] = count
        
        # Calculate conversation metrics
        conversation_length = len(history)
        pause_count = sum(1 for item in history if item is None)
        early_termination = conversation_length < config.conversation_length
        
        # Count unique items used
        unique_items = set()
        for item in history:
            if item is not None:
                unique_items.add(item.id)
        
        return SimulationResult(
            config=config,
            total_score=total_score,
            player_scores=player_scores,
            player_contributions=player_contributions,
            conversation_length=conversation_length,
            early_termination=early_termination,
            pause_count=pause_count,
            unique_items_used=len(unique_items),
            execution_time=execution_time
        )
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5


def run_altruism_sweep():
    """Run a parameter sweep testing different altruism probabilities."""
    simulator = MonteCarloSimulator()
    
    # Test different altruism probabilities
    altruism_probs = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    
    print("Starting altruism probability sweep...")
    results = simulator.run_parameter_sweep(
        altruism_probs=altruism_probs,
        num_simulations=50,
        base_players={'p10': 1, 'p0': 1, 'p1': 1, 'p2': 1}
    )
    
    # Analyze results
    analysis = simulator.analyze_results()
    
    # Print summary
    print("\n=== SIMULATION RESULTS ===")
    print(f"Total simulations: {analysis['total_simulations']}")
    print(f"Unique configurations: {analysis['unique_configurations']}")
    
    print("\n=== TOP 5 CONFIGURATIONS ===")
    for i, config in enumerate(analysis['best_configurations'], 1):
        print(f"{i}. Altruism: {config['config'][0]:.1f}, "
              f"Mean Score: {config['mean_score']:.2f}")
    
    # Save results
    filename = simulator.save_results()
    print(f"\nResults saved to: {filename}")
    
    return simulator, analysis


if __name__ == "__main__":
    run_altruism_sweep()
