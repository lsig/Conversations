"""
Player registry for randomly selecting opponents during training.
"""

import random
import sys
from typing import List, Type, Dict, Any

import sys
import os
# Add the project root to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

from models.player import Player, PlayerSnapshot, GameContext

# Import all available player types
from players.random_player import RandomPlayer
from players.pause_player import PausePlayer
from players.random_pause_player import RandomPausePlayer
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


class PlayerRegistry:
    """Registry for managing available player types for training."""
    
    def __init__(self):
        # Define available player classes with their names
        self.player_classes: Dict[str, Type[Player]] = {
            'RandomPlayer': RandomPlayer,
            'PausePlayer': PausePlayer,
            'RandomPausePlayer': RandomPausePlayer,
            'Player0': Player0,
            'Player1': Player1,
            'Player2': Player2,
            'Player3': Player3,
            'Player4': Player4,
            'Player5': Player5,
            'Player6': Player6,
            'Player7': Player7,
            'Player8': Player8,
            'Player9': Player9,
        }
        
        # Filter out players that might have issues (like Player0 which has different constructor)
        self.working_players = {
            'RandomPlayer': RandomPlayer,
            'PausePlayer': PausePlayer,
            'RandomPausePlayer': RandomPausePlayer,
            'Player1': Player1,
            'Player2': Player2,
            'Player3': Player3,
            'Player4': Player4,
            'Player5': Player5,
            'Player6': Player6,
            'Player7': Player7,
            'Player8': Player8,
            'Player9': Player9,
        }
    
    def get_random_player_class(self) -> Type[Player]:
        """Get a random player class."""
        return random.choice(list(self.working_players.values()))
    
    def get_random_player_classes(self, count: int) -> List[Type[Player]]:
        """Get multiple random player classes."""
        return [self.get_random_player_class() for _ in range(count)]
    
    def get_player_names(self) -> List[str]:
        """Get list of all available player names."""
        return list(self.working_players.keys())
    
    def get_player_class(self, name: str) -> Type[Player]:
        """Get a specific player class by name."""
        return self.working_players[name]
    
    def create_player_instance(self, player_class: Type[Player], snapshot: PlayerSnapshot, ctx: GameContext) -> Player:
        """Create an instance of a player class."""
        try:
            # Handle different constructor signatures
            if player_class == Player0:
                # Player0 has different constructor signature
                return player_class(snapshot, ctx.conversation_length)
            else:
                return player_class(snapshot, ctx)
        except Exception as e:
            print(f"Warning: Failed to create {player_class.__name__}: {e}")
            # Fallback to RandomPlayer
            return RandomPlayer(snapshot, ctx)


# Global registry instance
player_registry = PlayerRegistry()


def get_random_opponents(count: int = 9) -> List[Type[Player]]:
    """Get random opponent player classes."""
    return player_registry.get_random_player_classes(count)


def create_opponent_instances(opponent_classes: List[Type[Player]], snapshots: List[PlayerSnapshot], ctx: GameContext) -> List[Player]:
    """Create instances of opponent players."""
    opponents = []
    for i, player_class in enumerate(opponent_classes):
        if i < len(snapshots):
            opponent = player_registry.create_player_instance(player_class, snapshots[i], ctx)
            opponents.append(opponent)
    return opponents


if __name__ == "__main__":
    # Test the registry
    registry = PlayerRegistry()
    print("Available players:", registry.get_player_names())
    
    # Test random selection
    random_players = get_random_opponents(5)
    print("Random players:", [p.__name__ for p in random_players])
