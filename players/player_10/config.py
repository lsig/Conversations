"""
Configuration constants and hyperparameters for Player10.

This module contains all the tunable parameters for the lean-cut agent proposal,
with defaults that preserve the original behavior when altruism_use_prob = 0.0.
"""

# Altruism hyperparameters
ALTRUISM_USE_PROB = 0.0  # Per-turn probability to use altruism policy (0.0 = original behavior)
TAU_MARGIN = 0.05        # Altruism margin: speak if Δ_self ≥ E[Δ_others] - τ
EPSILON_FRESH = 0.05     # Lower τ by ε if (last was pause) AND (our best item is fresh)
EPSILON_MONO = 0.05      # Raise τ by ε if our best item would trigger monotony
MIN_SAMPLES_PID = 3      # Trust per-player mean after this many samples; else use global mean

# EWMA parameters
EWMA_ALPHA = 0.10        # Learning rate for exponential weighted moving average

# Selection forecast parameters
CURRENT_SPEAKER_EDGE = 0.5  # Weight bonus for current speaker
FAIRNESS_PROB_WITH_SPEAKER = 0.5  # Probability of fairness step when current speaker exists
FAIRNESS_PROB_NO_SPEAKER = 1.0    # Probability of fairness step when no current speaker

# Scoring component weights (canonical delta scorer)
IMPORTANCE_WEIGHT = 1.0
COHERENCE_WEIGHT = 1.0
FRESHNESS_WEIGHT = 1.0
MONOTONY_WEIGHT = 1.0  # Note: monotony is subtracted, so this is actually -1.0 in practice

# Context window sizes
FRESHNESS_WINDOW = 5     # Look back 5 turns for freshness calculation
COHERENCE_WINDOW = 3     # Look back 3 turns for coherence calculation
MONOTONY_WINDOW = 3      # Look back 3 turns for monotony detection

# Safety thresholds
MAX_CONSECUTIVE_PAUSES = 2  # Always propose if this many consecutive pauses
