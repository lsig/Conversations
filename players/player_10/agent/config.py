"""
Configuration constants and hyperparameters for Player10.

This module contains all the tunable parameters for the lean-cut agent proposal,
with optimized defaults based on Monte Carlo simulation results:
- Altruism=0.5, Tau=0.10, Fresh=0.05, Mono=0.05
- Achieves Total Score: 109.50 ± 7.08, Player10 Score: 2.76 ± 0.14
"""

# Altruism hyperparameters (optimized configuration)
ALTRUISM_USE_PROB = 0.5  # Per-turn probability to use altruism policy (optimized: 0.5)
TAU_MARGIN = 0       # Altruism margin: speak if Δ_self ≥ E[Δ_others] - τ (optimized: 0.10)
EPSILON_FRESH = 0.05     # Lower τ by ε if (last was pause) AND (our best item is fresh)
EPSILON_MONO = 0.25      # Raise τ by ε if our best item would trigger monotony
MIN_SAMPLES_PID = 5      # Trust per-player mean after this many samples; else use global mean

# EWMA parameters
EWMA_ALPHA = 0.05        # Learning rate for exponential weighted moving average

# Selection forecast parameters
CURRENT_SPEAKER_EDGE = 0.5  # Weight bonus for current speaker
FAIRNESS_PROB_WITH_SPEAKER = 0.5  # Probability of fairness step when current speaker exists
FAIRNESS_PROB_NO_SPEAKER = 1.0    # Probability of fairness step when no current speaker

# Scoring component weights (canonical delta scorer)
IMPORTANCE_WEIGHT = 1.0 # * (1-ALTRUISM_USE_PROB)
COHERENCE_WEIGHT = 1.0 
FRESHNESS_WEIGHT = 1.0
MONOTONY_WEIGHT = 2.0 # Note: monotony is subtracted, so this is actually -1.0 in practice

# Context window sizes
FRESHNESS_WINDOW = 5     # Look back 5 turns for freshness calculation
COHERENCE_WINDOW = 3     # Look back 3 turns for coherence calculation
MONOTONY_WINDOW = 3      # Look back 3 turns for monotony detection

# Safety thresholds
MAX_CONSECUTIVE_PAUSES = 2  # Always propose if this many consecutive pauses

# Debugging parameters
DEBUG_ENABLED = False  # Master debug toggle - set to True to enable detailed logging
DEBUG_LEVEL = 1        # Debug level: 1=basic, 2=detailed, 3=verbose
DEBUG_STRATEGY_SELECTION = True   # Log strategy selection (altruism vs original)
DEBUG_ITEM_EVALUATION = True      # Log item scoring and evaluation
DEBUG_ALTRUISM_GATE = True        # Log altruism gate decisions
DEBUG_PERFORMANCE_TRACKING = True # Log performance tracking updates
DEBUG_SELECTION_FORECAST = True   # Log selection forecasting
DEBUG_SAFETY_CHECKS = True        # Log safety checks and failsafes
