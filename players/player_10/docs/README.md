# Player10 - Lean-Cut Agent with Stochastic Altruism

This directory contains the redesigned Player10 implementation with a clean, modular structure and an optional altruism layer.

## File Structure

```
players/player_10/
├── player.py          # Main Player10 class with stochastic strategy selection
├── scoring.py         # Canonical delta scorer and EWMA performance tracking
├── strategies.py      # Original and altruism decision strategies
├── utils.py          # Helper functions for history analysis and item filtering
├── config.py         # Hyperparameters and configuration constants
├── test_player10.py  # Simple test to verify default behavior
└── README.md         # This file
```

## Key Features

### 1. **Backward Compatibility**
- **Default behavior**: When `ALTRUISM_USE_PROB = 0.0`, behavior is identical to the original Player10
- **No breaking changes**: All existing methods (`get_cumulative_score`, `get_game_state`) are preserved
- **Same API**: The `propose_item(history)` method works exactly as before

### 2. **Stochastic Altruism**
- **Controlled mixing**: Use `ALTRUISM_USE_PROB` to control the probability of using altruism vs. original strategy
- **Spec-faithful selection**: Models the 0.5 current-speaker edge, then uniform within first proposer tier
- **Player-specific performance tracking**: EWMA-based skill estimation per player
- **Context-aware decisions**: Adjusts thresholds based on freshness and monotony risks

### 3. **Clean Modular Design**
- **Single responsibility**: Each module has a clear, focused purpose
- **Familiar patterns**: Uses common Python module names (utils.py, config.py) that engineers expect
- **Easy to extend**: Add new strategies or modify existing ones without touching core logic
- **Well-documented**: Comprehensive docstrings and type hints throughout

## Configuration

### Hyperparameters (in `config.py`)

```python
# Altruism control
ALTRUISM_USE_PROB = 0.0  # Per-turn probability to use altruism (0.0 = original behavior)

# Altruism thresholds
TAU_MARGIN = 0.05        # Base altruism margin
EPSILON_FRESH = 0.05     # Lower τ if fresh after pause
EPSILON_MONO = 0.05      # Raise τ if would trigger monotony

# Performance tracking
MIN_SAMPLES_PID = 3      # Trust per-player mean after this many samples
EWMA_ALPHA = 0.10        # Learning rate for performance tracking
```

### Usage Examples

```python
# Original behavior (default)
# ALTRUISM_USE_PROB = 0.0

# Light altruism adoption
# ALTRUISM_USE_PROB = 0.2

# Full altruism mode
# ALTRUISM_USE_PROB = 1.0
```

## Strategy Selection

The player uses a **stochastic switch** between two strategies:

1. **Original Strategy**: The exact behavior of the original Player10
2. **Altruism Strategy**: Selection-aware decision making with performance tracking

Each turn, a coin is flipped with probability `ALTRUISM_USE_PROB` to choose the strategy.

## Altruism Logic

The altruism strategy implements:

1. **Selection Forecasting**: Models who is likely to be selected next based on:
   - 0.5 weight bonus for current speaker
   - Uniform distribution within first proposer tier (minimum contribution count)

2. **Performance Tracking**: Maintains EWMA of delta scores for:
   - Global performance (all players)
   - Per-player performance (after sufficient samples)

3. **Altruism Gate**: Proposes if:
   ```
   Δ_self ≥ E[Δ_others] - τ
   ```
   Where τ is adjusted based on context (freshness, monotony risk)

4. **Safety Mechanisms**: Always proposes if two consecutive pauses to avoid game termination

## Motivation

Earlier versions spoke when our best item’s score beat a global average threshold (not recent). The altruism variant refines this by comparing against a selection-weighted expectation of other players’ learned quality: speak if `Δ_self ≥ E[Δ_others] - τ`. This accounts for who is most likely to speak next (current speaker edge + fairness among the minimum-contribution tier) and how good they have been (EWMA). See `STRATEGIES.md` for details on τ adjustments, freshness, and monotony.

## Testing

Run the test to verify default behavior:

```bash
python -m players.player_10.test_player10
```

This ensures that when `ALTRUISM_USE_PROB = 0.0`, the player behaves identically to the original implementation.

## Future Extensions

The modular design makes it easy to add:

- **New strategies**: Add them to `strategies.py`
- **Advanced performance models**: Extend `PlayerPerformanceTracker` in `scoring.py`
- **Different selection models**: Modify `calculate_selection_weights` in `utils.py`
- **RL integration**: Use the existing `get_game_state` method for training

## Migration Guide

To use the new Player10:

1. **No changes needed** if using default settings (`ALTRUISM_USE_PROB = 0.0`)
2. **Enable altruism** by setting `ALTRUISM_USE_PROB > 0.0` in `config.py`
3. **Tune parameters** in `config.py` as needed for your use case

The player maintains full backward compatibility while providing powerful new capabilities for advanced decision making.
