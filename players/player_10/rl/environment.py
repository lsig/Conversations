import gymnasium as gym
import numpy as np
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import Counter
from dataclasses import asdict

import sys
import os

# Add the project root to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

from core.engine import Engine
from models.item import Item
from models.player import GameContext, Player, PlayerSnapshot
from .player import RLPlayer


class ConversationRLEnv(gym.Env):
	"""
	Gym environment for the conversation game with RL agent.

	The environment maintains the exact logic of the original engine but allows
	one player (the RL agent) to be controlled by an RL algorithm.
	"""

	metadata = {}

	def __init__(
		self,
		opponent_players: List[type[Player]],
		player_count: int = 4,
		subjects: int = 20,
		memory_size: int = 10,
		conversation_length: int = 20,
		max_history_length: int = 50,
		seed: Optional[int] = None,
	):
		super().__init__()

		self.opponent_players = opponent_players
		self.player_count = player_count
		self.subjects = subjects
		self.memory_size = memory_size
		self.conversation_length = conversation_length
		self.max_history_length = max_history_length

		# Set up random seed
		if seed is not None:
			self.seed(seed)

		# Action space: 0 = pass, 1 to memory_size = propose item from memory bank
		self.action_space = gym.spaces.Discrete(memory_size + 1)

		# Observation space components (only what player can see via propose_item API):
		# 1. Current conversation history (last max_history_length items)
		# 2. Agent's memory bank
		# 3. Agent's preferences
		# 4. Basic game context (conversation_length, number_of_players)

		history_dim = max_history_length * (subjects + 1)  # subjects + importance
		memory_dim = memory_size * (subjects + 1)  # subjects + importance
		preferences_dim = subjects
		context_dim = 2  # conversation_length, number_of_players

		total_obs_dim = history_dim + memory_dim + preferences_dim + context_dim

		self.observation_space = gym.spaces.Box(
			low=-np.inf, high=np.inf, shape=(total_obs_dim,), dtype=np.float32
		)

		# Initialize engine and agent
		self._initialize_engine()

	def seed(self, seed: Optional[int] = None) -> None:
		"""Set random seed for reproducibility."""
		if seed is not None:
			random.seed(seed)
			np.random.seed(seed)

	def _initialize_engine(self) -> None:
		"""Initialize the game engine with RL agent and opponents."""
		# Create a custom RLPlayer class with the correct observation dimension
		observation_dim = self.observation_space.shape[0]

		# Capture variables for the closure
		env_subjects = self.subjects
		env_max_history_length = self.max_history_length

		class CustomRLPlayer(RLPlayer):
			def __init__(self, snapshot, ctx):
				super().__init__(snapshot, ctx, observation_dim, env_max_history_length)
				self.subjects = list(range(env_subjects))  # Use environment's subjects

		# Create player types list: RL agent first, then opponents
		player_types = [CustomRLPlayer] + self.opponent_players

		# Assert that we have exactly the right number of player types
		assert len(player_types) == self.player_count, (
			f'Expected {self.player_count} player types, got {len(player_types)}'
		)

		# Initialize engine
		self.engine = Engine(
			players=player_types,
			player_count=self.player_count,
			subjects=self.subjects,
			memory_size=self.memory_size,
			conversation_length=self.conversation_length,
			seed=random.randint(0, 2**31 - 1),
		)

		# Find the RL agent (should be the first player)
		if len(self.engine.players) > 0:
			self.agent_player = self.engine.players[0]  # First player is the RL agent
			self.agent_id = self.agent_player.id
			# Set training mode for RL training
			self.agent_player.set_training_mode(True)
		else:
			raise RuntimeError('No players found in engine')

	def _encode_item(self, item: Optional[Item]) -> np.ndarray:
		"""Encode an item into a fixed-size vector."""
		if item is None:
			# Return zero vector for None items
			return np.zeros(self.subjects + 1, dtype=np.float32)

		# Create one-hot encoding for subjects
		subject_vector = np.zeros(self.subjects, dtype=np.float32)
		for subject in item.subjects:
			if 0 <= subject < self.subjects:
				subject_vector[subject] = 1.0

		# Add importance as the last element
		importance_vector = np.array([item.importance], dtype=np.float32)

		return np.concatenate([subject_vector, importance_vector])

	def _encode_history(self) -> np.ndarray:
		"""Encode conversation history into observation vector."""
		history_vector = np.zeros(self.max_history_length * (self.subjects + 1), dtype=np.float32)

		# Take the last max_history_length items
		recent_history = self.engine.history[-self.max_history_length :]

		for i, item in enumerate(recent_history):
			start_idx = i * (self.subjects + 1)
			end_idx = start_idx + (self.subjects + 1)
			history_vector[start_idx:end_idx] = self._encode_item(item)

		return history_vector

	def _encode_memory_bank(self) -> np.ndarray:
		"""Encode agent's memory bank into observation vector."""
		memory_vector = np.zeros(self.memory_size * (self.subjects + 1), dtype=np.float32)

		for i, item in enumerate(self.agent_player.memory_bank):
			start_idx = i * (self.subjects + 1)
			end_idx = start_idx + (self.subjects + 1)
			memory_vector[start_idx:end_idx] = self._encode_item(item)

		return memory_vector

	def _encode_preferences(self) -> np.ndarray:
		"""Encode agent's preferences into observation vector."""
		preferences_vector = np.zeros(self.subjects, dtype=np.float32)

		for i, subject in enumerate(self.agent_player.preferences):
			if 0 <= subject < self.subjects:
				# Higher preference = higher value (inverse of position)
				preferences_vector[subject] = 1.0 - (i / len(self.agent_player.preferences))

		return preferences_vector

	def _encode_context(self) -> np.ndarray:
		"""Encode game context into observation vector (only what player can see)."""
		context_vector = np.array(
			[
				self.agent_player.conversation_length / 100.0,  # Normalized conversation length
				self.agent_player.number_of_players / 10.0,  # Normalized player count
			],
			dtype=np.float32,
		)

		return context_vector

	def _get_observation(self) -> np.ndarray:
		"""Get current observation state (only what player can see via propose_item API)."""
		history_obs = self._encode_history()
		memory_obs = self._encode_memory_bank()
		preferences_obs = self._encode_preferences()
		context_obs = self._encode_context()

		return np.concatenate([history_obs, memory_obs, preferences_obs, context_obs])

	def _get_engine_proposals_with_agent_action(
		self, agent_action: int
	) -> dict[uuid.UUID, Item | None]:
		"""Get proposals from all players, including the agent's action."""
		# Set agent's action BEFORE getting proposals
		self.agent_player.set_action(agent_action)

		proposals = {}

		for player in self.engine.players:
			if player.id == self.agent_id:
				# Get agent's proposal (will use the set action in training mode)
				proposal = self.agent_player.propose_item(self.engine.history)
				if proposal and self.engine.snapshots[player.id].item_in_memory_bank(proposal):
					proposals[player.id] = proposal
			else:
				# Get opponent proposals
				proposal = player.propose_item(self.engine.history)
				if proposal and self.engine.snapshots[player.id].item_in_memory_bank(proposal):
					proposals[player.id] = proposal

		return proposals

	def reset(
		self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
	) -> Tuple[np.ndarray, Dict[str, Any]]:
		"""Reset the environment to initial state."""
		if seed is not None:
			self.seed(seed)

		# Reinitialize engine
		self._initialize_engine()

		# Get initial observation
		observation = self._get_observation()
		info = {
			'turn': 0,
			'conversation_length': self.conversation_length,
			'agent_id': str(self.agent_id),
			'memory_bank_size': len(self.agent_player.memory_bank),
		}

		return observation, info

	def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
		"""Execute one step in the environment using proper engine turn logic."""
		# Validate action
		if not self.action_space.contains(action):
			raise ValueError(f'Invalid action {action}. Must be in range [0, {self.memory_size}]')

		# Check if game is already over
		if self.engine.turn >= self.conversation_length or self.engine.consecutive_pauses >= 3:
			observation = self._get_observation()
			return observation, 0.0, True, False, {'turn': self.engine.turn, 'is_agent_turn': False}

		# Get proposals from all players, including agent's action
		proposals = self._get_engine_proposals_with_agent_action(action)

		# Use engine's proper speaker selection logic
		speaker, item = self.engine._Engine__select_speaker(proposals)

		# Update engine state exactly as the engine would
		if speaker:
			self.engine.history.append(item)
			self.engine.last_player_id = speaker
			self.engine.consecutive_pauses = 0
			self.engine.player_contributions[speaker].append(item)
		else:
			self.engine.history.append(None)
			self.engine.last_player_id = None
			self.engine.consecutive_pauses += 1

		self.engine.turn += 1

		# Calculate reward only if the agent was the speaker
		if speaker == self.agent_id:
			reward = self._calculate_agent_reward(item)
			is_agent_turn = True
		else:
			reward = 0.0
			is_agent_turn = False

		# Get observation and check termination
		observation = self._get_observation()
		terminated = (
			self.engine.turn >= self.conversation_length or self.engine.consecutive_pauses >= 3
		)

		# Calculate score impact for the turn
		score_impact = self.engine._calculate_turn_score_impact(item)

		info = {
			'turn': self.engine.turn,
			'speaker_id': str(speaker) if speaker else None,
			'speaker_name': self.engine.player_names.get(speaker, ''),
			'item': item,
			'score_impact': score_impact,
			'is_agent_turn': is_agent_turn,
			'proposals': {str(pid): prop for pid, prop in proposals.items()},
		}

		return observation, reward, terminated, False, info

	def _calculate_agent_reward(self, item: Optional[Item]) -> float:
		"""Calculate reward for the agent's action."""
		if item is None:
			return 0.0

		# Use the engine's score impact calculation
		score_impact = self.engine._calculate_turn_score_impact(item)

		# Return the total score impact as reward
		return score_impact.get('total', 0.0)

	def get_policy_network(self):
		"""Get the policy network for training."""
		return self.agent_player.get_policy_network()

	def set_opponent_classes(self, opponent_classes: List[type[Player]]):
		"""Update the opponent player classes."""
		self.opponent_players = opponent_classes
		# Reinitialize the engine with new opponents
		self._initialize_engine()

	def set_training_mode(self, training: bool) -> None:
		"""Set whether the agent is in training mode."""
		self.agent_player.set_training_mode(training)

	def close(self) -> None:
		"""Clean up resources."""
		pass
