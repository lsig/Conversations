"""
Player registry for randomly selecting opponents during training.
"""

import os
import random
import sys

# Add the project root to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

# Import after path setup
from models.player import GameContext, Player, PlayerSnapshot  # noqa: E402
from players.pause_player import PausePlayer  # noqa: E402
from players.player_0.player import Player0  # noqa: E402
from players.player_1.player import Player1  # noqa: E402
from players.player_2.player import Player2  # noqa: E402
from players.player_3.player import Player3  # noqa: E402
from players.player_4.player import Player4  # noqa: E402
from players.player_5.player import Player5  # noqa: E402
from players.player_6.player import Player6  # noqa: E402
from players.player_7.player import Player7  # noqa: E402
from players.player_8.player import Player8  # noqa: E402
from players.player_9.player import Player9  # noqa: E402
from players.random_pause_player import RandomPausePlayer  # noqa: E402
from players.random_player import RandomPlayer  # noqa: E402


class PlayerRegistry:
	"""Registry for managing available player types for training."""

	def __init__(self):
		# Define available player classes with their names
		self.player_classes: dict[str, type[Player]] = {
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

	def get_random_player_class(self) -> type[Player]:
		"""Get a random player class."""
		return random.choice(list(self.working_players.values()))

	def get_random_player_classes(self, count: int) -> list[type[Player]]:
		"""Get multiple random player classes."""
		return [self.get_random_player_class() for _ in range(count)]

	def get_player_names(self) -> list[str]:
		"""Get list of all available player names."""
		return list(self.working_players.keys())

	def get_player_class(self, name: str) -> type[Player]:
		"""Get a specific player class by name."""
		return self.working_players[name]

	def create_player_instance(
		self, player_class: type[Player], snapshot: PlayerSnapshot, ctx: GameContext
	) -> Player:
		"""Create an instance of a player class."""
		try:
			# Handle different constructor signatures
			if player_class == Player0:
				# Player0 has different constructor signature
				return player_class(snapshot, ctx.conversation_length)
			else:
				return player_class(snapshot, ctx)
		except Exception as e:
			print(f'Warning: Failed to create {player_class.__name__}: {e}')
			# Fallback to RandomPlayer
			return RandomPlayer(snapshot, ctx)


# Global registry instance
player_registry = PlayerRegistry()


def get_random_opponents(count: int = 9) -> list[type[Player]]:
	"""Get random opponent player classes."""
	return player_registry.get_random_player_classes(count)


def create_opponent_instances(
	opponent_classes: list[type[Player]], snapshots: list[PlayerSnapshot], ctx: GameContext
) -> list[Player]:
	"""Create instances of opponent players."""
	opponents = []
	for i, player_class in enumerate(opponent_classes):
		if i < len(snapshots):
			opponent = player_registry.create_player_instance(player_class, snapshots[i], ctx)
			opponents.append(opponent)
	return opponents


if __name__ == '__main__':
	# Test the registry
	registry = PlayerRegistry()
	print('Available players:', registry.get_player_names())

	# Test random selection
	random_players = get_random_opponents(5)
	print('Random players:', [p.__name__ for p in random_players])
