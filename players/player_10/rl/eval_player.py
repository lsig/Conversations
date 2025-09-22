"""
Evaluation player that loads a trained DQN model and uses it for inference.
"""

import glob
import os
import sys

import numpy as np
import torch

# Add the project root to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

# Import after path setup
from models.player import GameContext, Item, PlayerSnapshot  # noqa: E402

from .player import RLPlayer  # noqa: E402


class EvalPlayer(RLPlayer):
	"""Evaluation player that loads a trained model and uses it for inference."""

	def __init__(
		self,
		snapshot: PlayerSnapshot,
		ctx: GameContext,
		model_path: str | None = None,
		device: str = 'cpu',
	):
		"""
		Initialize evaluation player with a trained model.

		Args:
			snapshot: Player snapshot
			ctx: Game context
			model_path: Path to the trained model file (if None, auto-loads latest)
			device: Device to run inference on
		"""
		self.device = torch.device(device)
		print(f'🔍 EvalPlayer using device: {self.device}')

		# Auto-load latest model if no path provided
		if model_path is None:
			model_path = self._find_latest_model()

		self.model_path = model_path

		# Load model first to get the correct dimensions
		self._load_model_info()

		# Initialize with correct dimensions
		super().__init__(snapshot, ctx, observation_dim=self.obs_dim, max_history_length=20)

		# Load the actual model weights
		self._load_model_weights()

		# Set to inference mode (not training)
		self.set_training_mode(False)

	def _find_latest_model(self) -> str:
		"""Find the latest trained model file."""
		# Get the directory where this file is located
		current_dir = os.path.dirname(os.path.abspath(__file__))

		# Look for model files in the runs directory relative to current location
		model_patterns = [
			os.path.join(current_dir, 'runs/*/conversation_dqn_1M_network.pth'),  # From train.sh
			os.path.join(
				current_dir, 'runs/*/conversation_dqn_network.pth'
			),  # From manual training
			os.path.join(current_dir, 'runs/*/*_network.pth'),  # Any network file
			os.path.join(current_dir, 'runs/*/*.pth'),  # Any model file
			# Also check parent directories in case runs is at a higher level
			os.path.join(os.path.dirname(current_dir), 'runs/*/conversation_dqn_1M_network.pth'),
			os.path.join(os.path.dirname(current_dir), 'runs/*/conversation_dqn_network.pth'),
			os.path.join(os.path.dirname(current_dir), 'runs/*/*_network.pth'),
			os.path.join(os.path.dirname(current_dir), 'runs/*/*.pth'),
		]

		latest_file = None
		latest_time = 0

		for pattern in model_patterns:
			files = glob.glob(pattern)
			for file_path in files:
				file_time = os.path.getmtime(file_path)
				if file_time > latest_time:
					latest_time = file_time
					latest_file = file_path

		if latest_file is None:
			raise FileNotFoundError(
				'No trained model found. Please train a model first using:\n'
				'cd <project_root>/players/player_10\n'
				'./rl/train.sh\n\n'
				'Or provide a specific model_path when creating the EvalPlayer.'
			)

		print(f'🤖 Auto-loading latest trained model: {latest_file}')
		print(f'📅 Model created: {os.path.getctime(latest_file)}')
		return latest_file

	def _load_model_info(self):
		"""Load model information to determine dimensions."""
		try:
			# Load the model state dict
			checkpoint = torch.load(self.model_path, map_location=self.device)

			# Handle different checkpoint formats
			if isinstance(checkpoint, dict):
				if 'q_network_state_dict' in checkpoint:
					state_dict = checkpoint['q_network_state_dict']
					# Get dimensions from checkpoint if available
					self.obs_dim = checkpoint.get('obs_dim', 100)
					self.action_dim = checkpoint.get('action_dim', 4)
				elif 'model_state_dict' in checkpoint:
					state_dict = checkpoint['model_state_dict']
					self.obs_dim = 100  # Default
					self.action_dim = 4  # Default
				elif 'q_network' in checkpoint:
					state_dict = checkpoint['q_network']
					self.obs_dim = 100  # Default
					self.action_dim = 4  # Default
				else:
					state_dict = checkpoint
					self.obs_dim = 100  # Default
					self.action_dim = 4  # Default
			else:
				state_dict = checkpoint
				self.obs_dim = 100  # Default
				self.action_dim = 4  # Default

			# Determine dimensions from the state dict if not available
			if hasattr(self, 'obs_dim') and self.obs_dim == 100:
				# Try to infer from the first layer
				first_layer_key = 'network.0.weight'
				if first_layer_key in state_dict:
					self.obs_dim = state_dict[first_layer_key].shape[1]
					self.action_dim = (
						state_dict['network.4.weight'].shape[0]
						if 'network.4.weight' in state_dict
						else 4
					)

			self.state_dict = state_dict

		except Exception as e:
			print(f'Error loading model info from {self.model_path}: {e}')
			raise

	def _load_model_weights(self):
		"""Load the actual model weights."""
		try:
			# Load the state dict into the policy network
			self.policy_network.load_state_dict(self.state_dict)
			self.policy_network.to(self.device)
			self.policy_network.eval()

			print(f'✅ Successfully loaded model from {self.model_path}')
			print('📊 Model details:')
			print(f'   - Observation dimension: {self.obs_dim}')
			print(f'   - Action dimension: {self.action_dim}')
			print(
				f'   - Number of parameters: {sum(p.numel() for p in self.policy_network.parameters()):,}'
			)
			print(f'   - Device: {self.device}')

		except Exception as e:
			print(f'❌ Error loading model weights from {self.model_path}: {e}')
			raise

	def propose_item(self, history: list[Item]) -> Item | None:
		"""
		Propose an item using the trained neural network.

		Args:
			history: Conversation history

		Returns:
			Proposed item or None (for pause)
		"""
		# Get observation from the environment
		observation = self._get_observation(history)

		# Convert to tensor
		obs_tensor = torch.FloatTensor(observation).unsqueeze(0).to(self.device)

		# Get Q-values from the network
		with torch.no_grad():
			q_values = self.policy_network(obs_tensor)
			action = torch.argmax(q_values, dim=1).item()

		# Convert action to item
		if action == len(self.memory_bank):
			# Pass action
			return None
		elif 0 <= action < len(self.memory_bank):
			return self.memory_bank[action]
		else:
			# Fallback to random choice
			return np.random.choice(self.memory_bank) if self.memory_bank else None

	def get_model_info(self) -> dict:
		"""Get information about the loaded model."""
		return {
			'model_path': self.model_path,
			'device': str(self.device),
			'observation_dim': self.policy_network.network[0].in_features,
			'action_dim': self.policy_network.network[-1].out_features,
			'num_parameters': sum(p.numel() for p in self.policy_network.parameters()),
		}


def create_eval_player(
	snapshot: PlayerSnapshot,
	ctx: GameContext,
	model_path: str | None = None,
	device: str = 'cpu',
) -> EvalPlayer:
	"""Factory function to create an evaluation player."""
	return EvalPlayer(snapshot, ctx, model_path, device)


if __name__ == '__main__':
	# Test the evaluation player
	import uuid

	# Create dummy snapshot and context
	snapshot = PlayerSnapshot(
		id=uuid.uuid4(), preferences=[1, 2, 3, 4, 5], memory_bank=[], contributed_items=[]
	)

	ctx = GameContext(conversation_length=50, number_of_players=10, subjects=list(range(20)))

	# Test creation (this will fail without a real model file)
	try:
		eval_player = create_eval_player(snapshot, ctx, 'test_model.pth')
		print('EvalPlayer created successfully')
		print('Model info:', eval_player.get_model_info())
	except Exception as e:
		print(f'Expected error (no model file): {e}')
