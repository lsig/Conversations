import uuid
import numpy as np
import torch
import torch.nn as nn
from typing import Optional, List, Tuple

import sys
import os

# Add the project root to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

from models.item import Item
from models.player import GameContext, Player, PlayerSnapshot


class RLPolicyNetwork(nn.Module):
	"""Neural network that maps observations to actions."""

	def __init__(self, observation_dim: int, action_dim: int, hidden_dim: int = 256):
		super().__init__()
		self.network = nn.Sequential(
			nn.Linear(observation_dim, hidden_dim),
			nn.ReLU(),
			nn.Linear(hidden_dim, hidden_dim),
			nn.ReLU(),
			nn.Linear(hidden_dim, action_dim),
		)

	def forward(self, observation: torch.Tensor) -> torch.Tensor:
		return self.network(observation)


class RLPlayer(Player):
	"""RL Agent player with neural network policy."""

	def __init__(
		self,
		snapshot: PlayerSnapshot,
		ctx: GameContext,
		observation_dim: int,
		max_history_length: int = 50,
	) -> None:
		super().__init__(snapshot, ctx)
		self.name = 'RLAgent'
		self.max_history_length = max_history_length
		self.subjects = list(range(20))  # Default subjects, should match environment

		# Initialize neural network
		action_dim = len(self.memory_bank) + 1  # +1 for pass action
		self.policy_network = RLPolicyNetwork(observation_dim, action_dim)

		# For training mode (when action is set externally)
		self._current_action: Optional[int] = None
		self._training_mode = False

	def _encode_item(self, item: Optional[Item]) -> np.ndarray:
		"""Encode an item into a fixed-size vector (same as environment)."""
		if item is None:
			# Return zero vector for None items
			return np.zeros(len(self.subjects) + 1, dtype=np.float32)

		# Create one-hot encoding for subjects
		subject_vector = np.zeros(len(self.subjects), dtype=np.float32)
		for subject in item.subjects:
			if 0 <= subject < len(self.subjects):
				subject_vector[subject] = 1.0

		# Add importance as the last element
		importance_vector = np.array([item.importance], dtype=np.float32)

		return np.concatenate([subject_vector, importance_vector])

	def _encode_history(self, history: List[Item]) -> np.ndarray:
		"""Encode conversation history into observation vector (same as environment)."""
		history_vector = np.zeros(
			self.max_history_length * (len(self.subjects) + 1), dtype=np.float32
		)

		# Take the last max_history_length items
		recent_history = history[-self.max_history_length :]

		for i, item in enumerate(recent_history):
			start_idx = i * (len(self.subjects) + 1)
			end_idx = start_idx + (len(self.subjects) + 1)
			history_vector[start_idx:end_idx] = self._encode_item(item)

		return history_vector

	def _encode_memory_bank(self) -> np.ndarray:
		"""Encode agent's memory bank into observation vector (same as environment)."""
		memory_vector = np.zeros(len(self.memory_bank) * (len(self.subjects) + 1), dtype=np.float32)

		for i, item in enumerate(self.memory_bank):
			start_idx = i * (len(self.subjects) + 1)
			end_idx = start_idx + (len(self.subjects) + 1)
			memory_vector[start_idx:end_idx] = self._encode_item(item)

		return memory_vector

	def _encode_preferences(self) -> np.ndarray:
		"""Encode agent's preferences into observation vector (same as environment)."""
		preferences_vector = np.zeros(len(self.subjects), dtype=np.float32)

		for i, subject in enumerate(self.preferences):
			if 0 <= subject < len(self.subjects):
				# Higher preference = higher value (inverse of position)
				preferences_vector[subject] = 1.0 - (i / len(self.preferences))

		return preferences_vector

	def _encode_context(self) -> np.ndarray:
		"""Encode game context into observation vector (same as environment)."""
		context_vector = np.array(
			[
				self.conversation_length / 100.0,  # Normalized conversation length
				self.number_of_players / 10.0,  # Normalized player count
			],
			dtype=np.float32,
		)

		return context_vector

	def _get_observation(self, history: List[Item]) -> np.ndarray:
		"""Get current observation state (same encoding as environment)."""
		history_obs = self._encode_history(history)
		memory_obs = self._encode_memory_bank()
		preferences_obs = self._encode_preferences()
		context_obs = self._encode_context()

		return np.concatenate([history_obs, memory_obs, preferences_obs, context_obs])

	def propose_item(self, history: List[Item]) -> Optional[Item]:
		"""Propose item using neural network policy (standard player API)."""
		if self._training_mode and self._current_action is not None:
			# Training mode: use externally set action
			action = self._current_action
		else:
			# Inference mode: use neural network
			observation = self._get_observation(history)
			observation_tensor = torch.FloatTensor(observation).unsqueeze(0)

			with torch.no_grad():
				action_logits = self.policy_network(observation_tensor)
				action = torch.argmax(action_logits, dim=1).item()

		# Convert action to item
		if action == 0:
			return None  # Pass

		# Actions 1 to memory_bank_size correspond to items in memory bank
		if 1 <= action <= len(self.memory_bank):
			return self.memory_bank[action - 1]

		return None

	def set_action(self, action: int) -> None:
		"""Set the action for training mode."""
		self._current_action = action

	def set_training_mode(self, training: bool) -> None:
		"""Set whether the player is in training mode."""
		self._training_mode = training

	def get_policy_network(self) -> nn.Module:
		"""Get the policy network for training."""
		return self.policy_network
