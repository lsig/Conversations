#!/bin/bash

# DQN Training Script for Conversation Game
# This script trains a DQN agent to play the conversation game

echo "Starting DQN training for conversation game..."
echo "Training for 1,000,000 steps with 10 players (1 RL agent + 9 random opponents)"
echo "Memory size: 10, Subjects: 20, Conversation length: 50"
echo ""

# Activate the conversations environment (adjust path as needed)
if [ -f ~/anaconda3/etc/profile.d/conda.sh ]; then
    source ~/anaconda3/etc/profile.d/conda.sh
elif [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    source ~/miniconda3/etc/profile.d/conda.sh
fi

conda activate conversations

# Change to the directory containing this script
cd "$(dirname "$0")/.."

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo "🔍 GPU Status:"
    nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader,nounits
    echo ""
fi

# Run the training (force CUDA usage)
python -m rl.dqn \
    --total_timesteps 10000 \
    --learning_starts 1000 \
    --player_refresh_frequency 500 \
    --save_model True \
    --exp_name "conversation_dqn_10k" \
    --seed 42 \
    --cuda True

echo ""
echo "Training completed!"
echo "Model saved to runs/ directory"
echo "Use the EvalPlayer to load the trained model for evaluation"
