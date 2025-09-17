#!/usr/bin/env python3
"""
Testing script for running multiple iterations of the conversation simulation.

Usage:
    uv run python test_simulation.py --iterations 100 --subjects 20 --length 10 --player pr 3 --player p9 3
"""

import argparse
import json
import random
import statistics
from collections import defaultdict
from typing import Dict, List, Any

from core.engine import Engine
from core.utils import CustomEncoder
from models.player import Player
from players.pause_player import PausePlayer
from players.player_0.player import Player0
from players.player_1.player import Player1
from players.player_2.player import Player2
from players.player_3.player import Player3
from players.player_4.player import Player4
from players.player_5.player import Player5
from players.player_6.player import Player6
from players.player_7.player import Player7
from players.player_8.player import Player8
from players.player_9.player import Player9

from players.player_11.player import Player11
from players.random_pause_player import RandomPausePlayer
from players.random_player import RandomPlayer


# Player type mapping
PLAYER_TYPES = {
    'pr': RandomPlayer,
    'pp': PausePlayer,
    'prp': RandomPausePlayer,
    'p0': Player0,
    'p1': Player1,
    'p2': Player2,
    'p3': Player3,
    'p4': Player4,
    'p5': Player5,
    'p6': Player6,
    'p7': Player7,
    'p8': Player8,
    'p9': Player9,

    'p11': Player11,
}

DEFAULT_PLAYERS = {
    'p0': 0, 'p1': 0, 'p2': 0, 'p3': 0, 'p4': 0, 'p5': 0, 'p6': 0,
    'p7': 0, 'p8': 0, 'p9': 0, 'p10': 0, 'p11': 0,
    'pr': 0, 'pp': 0, 'prp': 0,
}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Run multiple iterations of the conversation simulation with random seeds.'
    )
    
    parser.add_argument(
        '--iterations', 
        type=int, 
        required=True
    )

    parser.add_argument(
        '--player',
        action='append',
        nargs=2,
        metavar=('TYPE', 'COUNT')
    )

    parser.add_argument('--subjects', type=int, default=20)

    parser.add_argument(
        '--memory_size', type=int, default=10
    )
    parser.add_argument(
        '--length', type=int, default=10
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default='test_results.json',
    )
    
    return parser.parse_args()


def run_single_simulation(players_config: Dict[str, int], subjects: int, memory_size: int, 
                         length: int, seed: int) -> Dict[str, Any]:
    """Run a single simulation with the given parameters."""
    

    players: List[type[Player]] = []
    for player_type, count in players_config.items():
        if count > 0 and player_type in PLAYER_TYPES:
            players.extend([PLAYER_TYPES[player_type]] * count)
    
    total_players = sum(players_config.values())
    
    # Create and run engine
    engine = Engine(
        players=players,
        player_count=total_players,
        subjects=subjects,
        memory_size=memory_size,
        conversation_length=length,
        seed=seed,
    )
    
    # Run simulation
    simulation_results = engine.run(players)
    
    return simulation_results


def group_scores_by_player_type(results: List[Dict[str, Any]], players_config: Dict[str, int]) -> Dict[str, Any]:
    """Group scores by player type rather than individual player ID."""
    
    # Create the players list in the same order as main.py
    players_list = []
    for ptype, count in players_config.items():
        if count > 0 and ptype in PLAYER_TYPES:
            players_list.extend([PLAYER_TYPES[ptype]] * count)
    
    # Create a mapping from player class name to player type code
    class_to_type = {}
    for ptype, player_class in PLAYER_TYPES.items():
        class_to_type[player_class.__name__] = ptype
    
    # Collect scores by player type
    type_scores = defaultdict(lambda: defaultdict(list))
    shared_score_breakdowns = []
    
    for result in results:
        shared_score_breakdowns.append(result['score_breakdown'])
        
        # Group player scores by type using the players list order
        player_scores = result['scores']['player_scores']
        
        # Map each player to its type based on the order in players_list
        for player_idx, player_data in enumerate(player_scores):
            if player_idx < len(players_list):
                player_class = players_list[player_idx]
                player_type = class_to_type.get(player_class.__name__, 'unknown')
                
                if 'scores' in player_data:
                    for score_type, value in player_data['scores'].items():
                        type_scores[player_type][score_type].append(value)
    
    # Calculate averages by type
    avg_type_scores = {}
    for ptype, scores in type_scores.items():
        avg_type_scores[ptype] = {}
        for score_type, values in scores.items():
            if values:
                avg_type_scores[ptype][score_type] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'stdev': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
    
    # Calculate average shared score breakdown
    avg_shared_breakdown = {}
    if shared_score_breakdowns:
        for key in shared_score_breakdowns[0].keys():
            values = [breakdown[key] for breakdown in shared_score_breakdowns]
            avg_shared_breakdown[key] = {
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0.0,
                'min': min(values),
                'max': max(values)
            }
    
    return {
        'player_type_scores': avg_type_scores,
        'shared_score_breakdown': avg_shared_breakdown,
        'total_iterations': len(results)
    }


def main():
    """Main function to run the testing script."""
    args = parse_arguments()
    
    # Parse player configuration
    players_config = DEFAULT_PLAYERS.copy()
    if args.player:
        for player_type, count_str in args.player:
            if player_type in players_config:
                players_config[player_type] = int(count_str)
            else:
                print(f"Warning: Unknown player type '{player_type}' ignored.")
    
    # Validate that we have at least one player
    total_players = sum(players_config.values())
    if total_players == 0:
        print("Error: No players specified. Use --player to add players.")
        return
    
    print(f"Running {args.iterations} iterations with {total_players} players...")
    print(f"Player configuration: {dict(players_config)}")
    print(f"Simulation parameters: subjects={args.subjects}, memory_size={args.memory_size}, length={args.length}")
    print()
    
    # Run simulations
    results = []
    for i in range(args.iterations):
        seed = random.randint(1, 9999999)  # Random seed between 1 and 7 digits
        if (i + 1) % 10 == 0 or i == 0:
            print(f"Completed {i + 1}/{args.iterations} iterations...")
        
        try:
            result = run_single_simulation(
                players_config=players_config,
                subjects=args.subjects,
                memory_size=args.memory_size,
                length=args.length,
                seed=seed
            )
            results.append(result)
        except Exception as e:
            print(f"Error in iteration {i + 1} (seed {seed}): {e}")
            continue
    
    if not results:
        print("No successful simulations completed.")
        return
    
    print(f"Successfully completed {len(results)} out of {args.iterations} iterations.")
    print()
    
    # Calculate averages
    print("Calculating averages...")
    averages = group_scores_by_player_type(results, players_config)
    
    # Print results
    print("\n" + "="*80)
    print("AVERAGE SCORES BY PLAYER TYPE")
    print("="*80)
    
    for ptype, scores in averages['player_type_scores'].items():
        print(f"\n{ptype.upper()}:")
        for score_type, stats in scores.items():
            print(f"  {score_type.capitalize()}:")
            print(f"    Mean: {stats['mean']:.4f}")
            print(f"    Median: {stats['median']:.4f}")
            print(f"    Std Dev: {stats['stdev']:.4f}")
            print(f"    Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
            print(f"    Sample Count: {stats['count']}")
    
    print("\n" + "="*80)
    print("AVERAGE SHARED SCORE BREAKDOWN")
    print("="*80)
    
    for score_type, stats in averages['shared_score_breakdown'].items():
        print(f"\n{score_type.capitalize()}:")
        print(f"  Mean: {stats['mean']:.4f}")
        print(f"  Median: {stats['median']:.4f}")
        print(f"  Std Dev: {stats['stdev']:.4f}")
        print(f"  Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
    
    # Save detailed results to file
    output_data = {
        'averages': averages
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2, cls=CustomEncoder)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == '__main__':
    main()