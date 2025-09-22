# DQN for Conversation Environment
import os
import random
import time
from dataclasses import dataclass

import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import argparse
from torch.utils.tensorboard import SummaryWriter

import sys
import os

# Add the project root to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.append(project_root)

from stable_baselines3.common.buffers import ReplayBuffer
from .environment import ConversationRLEnv
from .player import RLPlayer
from .player_registry import get_random_opponents, create_opponent_instances
from models.player import Player


@dataclass
class Args:
	exp_name: str = 'conversation_dqn'
	"""the name of this experiment"""
	seed: int = 1
	"""seed of the experiment"""
	torch_deterministic: bool = True
	"""if toggled, `torch.backends.cudnn.deterministic=False`"""
	cuda: bool = True
	"""if toggled, cuda will be enabled by default"""
	track: bool = False
	"""if toggled, this experiment will be tracked with Weights and Biases"""
	wandb_project_name: str = 'conversation-rl'
	"""the wandb's project name"""
	wandb_entity: str = None
	"""the entity (team) of wandb's project"""
	capture_video: bool = False
	"""whether to capture videos of the agent performances (check out `videos` folder)"""
	save_model: bool = True
	"""whether to save model into the `runs/{run_name}` folder"""
	upload_model: bool = False
	"""whether to upload the saved model to huggingface"""
	hf_entity: str = ''
	"""the user or org name of the model repository from the Hugging Face Hub"""

	# Conversation environment specific arguments
	player_count: int = 10
	"""number of players in the conversation (1 RL agent + 9 opponents)"""
	subjects: int = 20
	"""number of subjects in the conversation"""
	memory_size: int = 10
	"""size of each player's memory bank"""
	conversation_length: int = 50
	"""length of each conversation episode"""
	max_history_length: int = 20
	"""maximum history length for observations"""
	player_refresh_frequency: int = 100
	"""number of episodes between player refreshes"""

	# Algorithm specific arguments
	total_timesteps: int = 100000
	"""total timesteps of the experiments"""
	learning_rate: float = 2.5e-4
	"""the learning rate of the optimizer"""
	buffer_size: int = 10000
	"""the replay memory buffer size"""
	gamma: float = 0.99
	"""the discount factor gamma"""
	tau: float = 1.0
	"""the target network update rate"""
	target_network_frequency: int = 500
	"""the timesteps it takes to update the target network"""
	batch_size: int = 128
	"""the batch size of sample from the reply memory"""
	start_e: float = 1
	"""the starting epsilon for exploration"""
	end_e: float = 0.05
	"""the ending epsilon for exploration"""
	exploration_fraction: float = 0.5
	"""the fraction of `total-timesteps` it takes from start-e to go end-e"""
	learning_starts: int = 1000
	"""timestep to start learning"""
	train_frequency: int = 10
	"""the frequency of training"""


class RandomPlayer(Player):
	"""Random opponent player for training."""

	def propose_item(self, history):
		if self.memory_bank and random.random() < 0.7:  # 70% chance to propose
			return random.choice(self.memory_bank)
		return None


class GreedyPlayer(Player):
	"""Greedy opponent player for training."""

	def propose_item(self, history):
		# Find highest importance item not yet used
		used_items = {item.id for item in history if item}
		available_items = [item for item in self.memory_bank if item.id not in used_items]

		if available_items:
			return max(available_items, key=lambda x: x.importance)
		return None


# ALGO LOGIC: initialize agent here:
class QNetwork(nn.Module):
	def __init__(self, observation_dim: int, action_dim: int, hidden_dim: int = 256):
		super().__init__()
		self.network = nn.Sequential(
			nn.Linear(observation_dim, hidden_dim),
			nn.ReLU(),
			nn.Linear(hidden_dim, hidden_dim),
			nn.ReLU(),
			nn.Linear(hidden_dim, action_dim),
		)

	def forward(self, x):
		return self.network(x)


def linear_schedule(start_e: float, end_e: float, duration: int, t: int):
	slope = (end_e - start_e) / duration
	return max(slope * t + start_e, end_e)


if __name__ == '__main__':
	# Parse arguments manually since we don't have tyro
	parser = argparse.ArgumentParser()
	for field_name, field_info in Args.__dataclass_fields__.items():
		parser.add_argument(
			f'--{field_name}',
			type=type(getattr(Args(), field_name)),
			default=getattr(Args(), field_name),
			help=field_info.metadata.get('help', ''),
		)

	args = parser.parse_args()
	# Convert to Args object
	args = Args(**vars(args))
	run_name = f'{args.exp_name}__{args.seed}__{int(time.time())}'

	if args.track:
		import wandb

		wandb.init(
			project=args.wandb_project_name,
			entity=args.wandb_entity,
			sync_tensorboard=True,
			config=vars(args),
			name=run_name,
			save_code=True,
		)

	writer = SummaryWriter(f'runs/{run_name}')
	writer.add_text(
		'hyperparameters',
		'|param|value|\n|-|-|\n%s'
		% ('\n'.join([f'|{key}|{value}|' for key, value in vars(args).items()])),
	)

	# Seeding
	random.seed(args.seed)
	np.random.seed(args.seed)
	torch.manual_seed(args.seed)
	torch.backends.cudnn.deterministic = args.torch_deterministic

	# Force training to use GPU 0 if available, otherwise CPU
	if torch.cuda.is_available() and args.cuda:
		device = torch.device('cuda:0')
		print(f'🚀 Training on GPU 0: {torch.cuda.get_device_name(0)}')
		print(f'📊 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
	else:
		device = torch.device('cpu')
		print('💻 Training on CPU')

	# Get initial random opponents
	opponent_classes = get_random_opponents(args.player_count - 1)  # -1 for RL agent

	# Create conversation environment
	env = ConversationRLEnv(
		opponent_players=opponent_classes,
		player_count=args.player_count,
		subjects=args.subjects,
		memory_size=args.memory_size,
		conversation_length=args.conversation_length,
		max_history_length=args.max_history_length,
		seed=args.seed,
	)

	# Get observation and action dimensions
	obs_dim = env.observation_space.shape[0]
	action_dim = env.action_space.n

	# Initialize networks
	q_network = QNetwork(obs_dim, action_dim).to(device)
	optimizer = optim.Adam(q_network.parameters(), lr=args.learning_rate)
	target_network = QNetwork(obs_dim, action_dim).to(device)
	target_network.load_state_dict(q_network.state_dict())

	# Replay buffer
	rb = ReplayBuffer(
		args.buffer_size,
		env.observation_space,
		env.action_space,
		device,
		handle_timeout_termination=False,
		n_envs=1,
	)
	start_time = time.time()

	# Training loop
	obs, _ = env.reset()
	episode_reward = 0
	episode_length = 0

	for global_step in range(args.total_timesteps):
		# Action selection with epsilon-greedy
		epsilon = linear_schedule(
			args.start_e, args.end_e, args.exploration_fraction * args.total_timesteps, global_step
		)
		if random.random() < epsilon:
			action = env.action_space.sample()
		else:
			with torch.no_grad():
				q_values = q_network(torch.Tensor(obs).unsqueeze(0).to(device))
				action = torch.argmax(q_values, dim=1).cpu().numpy()[0]

		# Environment step
		next_obs, reward, terminated, truncated, info = env.step(action)
		episode_reward += reward
		episode_length += 1

		# Store in replay buffer
		rb.add(obs, next_obs, np.array([action]), np.array([reward]), np.array([terminated]), info)
		obs = next_obs

		# Episode finished
		if terminated or truncated:
			print(
				f'global_step={global_step}, episodic_return={episode_reward:.3f}, episode_length={episode_length}'
			)
			writer.add_scalar('charts/episodic_return', episode_reward, global_step)
			writer.add_scalar('charts/episodic_length', episode_length, global_step)
			if args.track:
				wandb.log(
					{
						'charts/episodic_return': episode_reward,
						'charts/episodic_length': episode_length,
						'charts/epsilon': epsilon,
					},
					step=global_step,
				)

			# Refresh opponents periodically
			if global_step % args.player_refresh_frequency == 0:
				new_opponents = get_random_opponents(args.player_count - 1)
				env.set_opponent_classes(new_opponents)
				print(f'Refreshed opponents at step {global_step}')

			# Reset for next episode
			obs, _ = env.reset()
			episode_reward = 0
			episode_length = 0

		# Training
		if global_step > args.learning_starts:
			if global_step % args.train_frequency == 0:
				data = rb.sample(args.batch_size)
				with torch.no_grad():
					target_max, _ = target_network(data.next_observations).max(dim=1)
					td_target = data.rewards.flatten() + args.gamma * target_max * (
						1 - data.dones.flatten()
					)
				old_val = q_network(data.observations).gather(1, data.actions).squeeze()
				loss = F.mse_loss(td_target, old_val)

				if global_step % 100 == 0:
					writer.add_scalar('losses/td_loss', loss, global_step)
					writer.add_scalar('losses/q_values', old_val.mean().item(), global_step)
					writer.add_scalar('charts/epsilon', epsilon, global_step)
					print('SPS:', int(global_step / (time.time() - start_time)))
					writer.add_scalar(
						'charts/SPS', int(global_step / (time.time() - start_time)), global_step
					)

					if args.track:
						wandb.log(
							{
								'losses/td_loss': loss.item(),
								'losses/q_values': old_val.mean().item(),
								'charts/epsilon': epsilon,
								'charts/SPS': int(global_step / (time.time() - start_time)),
							},
							step=global_step,
						)

				# Optimize the model
				optimizer.zero_grad()
				loss.backward()
				optimizer.step()

			# Update target network
			if global_step % args.target_network_frequency == 0:
				for target_network_param, q_network_param in zip(
					target_network.parameters(), q_network.parameters()
				):
					target_network_param.data.copy_(
						args.tau * q_network_param.data
						+ (1.0 - args.tau) * target_network_param.data
					)

	# Save model
	if args.save_model:
		model_path = f'runs/{run_name}/{args.exp_name}.pth'
		# Save comprehensive model information
		model_data = {
			'q_network_state_dict': q_network.state_dict(),
			'args': args,
			'obs_dim': obs_dim,
			'action_dim': action_dim,
			'total_timesteps': args.total_timesteps,
			'final_epsilon': epsilon,
		}
		torch.save(model_data, model_path)
		print(f'model saved to {model_path}')

		# Also save just the network for easy loading
		network_path = f'runs/{run_name}/{args.exp_name}_network.pth'
		torch.save(q_network.state_dict(), network_path)
		print(f'network saved to {network_path}')

	env.close()
	writer.close()
	if args.track:
		wandb.finish()
