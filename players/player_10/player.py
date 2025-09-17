"""
Player10 - Lean-cut agent with stochastic altruism.

This player implements the original Player10 behavior by default, with an optional
altruism layer that can be enabled via the ALTRUISM_USE_PROB hyperparameter.

When altruism_use_prob = 0.0, behavior is identical to the original Player10.
When altruism_use_prob > 0.0, the player stochastically switches between original
and altruism strategies each turn.
"""

import random
import uuid
from collections.abc import Sequence
from typing import Optional

from models.item import Item
from models.player import GameContext, Player, PlayerSnapshot

from .config import ALTRUISM_USE_PROB
from .scoring import PlayerPerformanceTracker, calculate_canonical_delta, is_pause
from .strategies import AltruismStrategy, OriginalStrategy


class Player10(Player):
    """
    Hybrid policy with optional altruism layer:
    
    • Turn 0 (empty history) → Edge-case opener:
        - Prefer single-subject item (coherence-friendly for others to echo),
          break ties by highest importance, random among top ties.
        - If no single-subject items exist, pick highest-importance overall.
    
    • If there are already two consecutive pauses → Keepalive:
        - Propose a safe, non-repeated item to avoid a 3rd pause ending the game
          (spec: "If there are three consecutive pauses, ... ends prematurely").
    
    • Immediately after a pause → Freshness maximizer:
        - Choose a non-repeated item whose subjects are novel w.r.t. the last
          5 non-pause turns before the pause (spec Freshness).
        - Prefer 2-subject items with both novel (+2), then 1 novel (+1),
          tie-break by importance.
    
    • Otherwise → General scoring (Player10-style) OR Altruism gate:
        - Original: Score = importance + coherence + freshness + nonmonotonousness
        - Altruism: Compare our best Δ vs selection-weighted expected Δ of others
        - Stochastic switch between strategies based on ALTRUISM_USE_PROB
    
    Spec rules cited:
        - Freshness: post-pause novel subjects (+1 / +2).
        - Nonrepetition: repeats have zero importance; also incur -1 nonmonotonousness.
        - Nonmonotonousness: subject appearing in each of previous three items → -1.
        - Early termination: three consecutive pauses end the conversation.
    """
    
    def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
        super().__init__(snapshot, ctx)
        
        # Initialize state tracking
        self._seen_item_ids: set[uuid.UUID] = set()
        self._S = len(self.preferences)
        self._rank1: dict[int, int] = {subj: i + 1 for i, subj in enumerate(self.preferences)}
        self.last_scores = []
        
        # Initialize performance tracking for altruism
        self.performance_tracker = PlayerPerformanceTracker()
        
        # Initialize strategies
        self.original_strategy = OriginalStrategy(self)
        self.altruism_strategy = AltruismStrategy(self, self.performance_tracker)
    
    def propose_item(self, history: list[Item | None]) -> Item | None:
        """
        Main decision method with stochastic strategy selection.
        
        Args:
            history: The conversation history
            
        Returns:
            An item to propose, or None to pass
        """
        # Update performance tracking with last turn's result
        self._update_performance_tracking(history)
        
        # Stochastic strategy selection
        use_altruism = random.random() < ALTRUISM_USE_PROB
        
        if use_altruism:
            return self.altruism_strategy.propose_item(history)
        else:
            return self.original_strategy.propose_item(history)
    
    def _update_performance_tracking(self, history: Sequence[Item | None]) -> None:
        """
        Update performance tracking with the last turn's realized delta.
        """
        if len(history) < 2:
            return
        
        # Get the last item and calculate its realized delta
        last_item = history[-1]
        if is_pause(last_item):
            return
        
        # Calculate delta for the last item
        turn_idx = len(history) - 1
        is_repeated = self._is_repeated(last_item, history[:-1])
        delta = calculate_canonical_delta(last_item, turn_idx, history, is_repeated)
        
        # Update performance tracking
        player_id = getattr(last_item, 'player_id', None)
        if player_id is not None:
            self.performance_tracker.update(player_id, delta)
    
    def _is_repeated(self, item: Item, history: Sequence[Item | None]) -> bool:
        """
        Check if an item has been played before in the history.
        """
        item_id = getattr(item, 'id', None)
        if item_id is None:
            return False
        
        for hist_item in history:
            if is_pause(hist_item):
                continue
            if getattr(hist_item, 'id', None) == item_id:
                return True
        
        return False
    
    def get_cumulative_score(self, history: list[Item | None]) -> dict[str, float]:
        """
        Calculate the cumulative score so far for each scoring component.
        
        This method is kept for backward compatibility and RL training purposes.
        
        Returns:
            Dictionary with cumulative scores for each component
        """
        if not history:
            return {
                'total': 0.0,
                'importance': 0.0,
                'coherence': 0.0,
                'freshness': 0.0,
                'nonmonotonousness': 0.0,
                'individual': 0.0,
            }
        
        total_importance = 0.0
        total_coherence = 0.0
        total_freshness = 0.0
        total_nonmonotonousness = 0.0
        total_individual = 0.0
        unique_items = set()
        
        for i, item in enumerate(history):
            if item is None:  # Skip pauses
                continue
            
            is_repeated = item.id in unique_items
            unique_items.add(item.id)
            
            if is_repeated:
                # Repeated items only contribute to nonmonotonousness
                total_nonmonotonousness -= 1.0
            else:
                # Calculate scores for non-repeated items
                total_importance += item.importance
                total_coherence += self._calculate_coherence_score(i, item, history)
                total_freshness += self._calculate_freshness_score(i, item, history)
                total_nonmonotonousness += self._calculate_nonmonotonousness_score(
                    i, item, False, history
                )
            
            # Calculate individual bonus
            bonuses = [
                1 - self.preferences.index(s) / len(self.preferences)
                for s in item.subjects
                if s in self.preferences
            ]
            if bonuses:
                total_individual += sum(bonuses) / len(bonuses)
        
        total_score = total_importance + total_coherence + total_freshness + total_nonmonotonousness
        
        return {
            'total': total_score,
            'importance': total_importance,
            'coherence': total_coherence,
            'freshness': total_freshness,
            'nonmonotonousness': total_nonmonotonousness,
            'individual': total_individual,
        }
    
    def get_game_state(self, history: list[Item | None]) -> dict:
        """
        Get a comprehensive game state representation for RL training.
        
        This method is kept for backward compatibility and RL training purposes.
        
        Returns:
            Dictionary containing game state information
        """
        cumulative_scores = self.get_cumulative_score(history)
        
        # Available items analysis
        available_items = []
        for item in self._iter_unused_items():
            if not self._is_repeated(item, history):
                turn_idx = len(history)
                impact = {
                    'total': calculate_canonical_delta(item, turn_idx, history, is_repeated=False),
                    'importance': item.importance,
                    'coherence': self._calculate_coherence_score(turn_idx, item, history),
                    'freshness': self._calculate_freshness_score(turn_idx, item, history),
                    'nonmonotonousness': self._calculate_nonmonotonousness_score(
                        turn_idx, item, False, history
                    ),
                }
                
                available_items.append({
                    'id': str(item.id),
                    'importance': item.importance,
                    'subjects': item.subjects,
                    'predicted_impact': impact,
                    'aligns_with_preferences': any(
                        s in self.preferences[:3] for s in item.subjects
                    ),
                })
        
        # Recent context analysis
        recent_context = {
            'last_was_pause': len(history) > 0 and is_pause(history[-1]),
            'consecutive_pauses': self._trailing_pause_count(history),
            'recent_subjects': set(),
            'our_contributions': 0,
        }
        
        # Analyze last 5 turns
        for item in history[-5:]:
            if item is not None:
                recent_context['recent_subjects'].update(item.subjects)
                if getattr(item, 'player_id', None) == self.id:
                    recent_context['our_contributions'] += 1
        
        recent_context['recent_subjects'] = list(recent_context['recent_subjects'])
        
        return {
            'cumulative_scores': cumulative_scores,
            'turn_info': {
                'turn_number': len(history),
                'consecutive_pauses': self._trailing_pause_count(history),
                'is_early_game': len(history) < 3,
                'is_late_game': len(history) > self.conversation_length * 0.7,
            },
            'available_items': available_items,
            'recent_context': recent_context,
            'preferences': self.preferences,
        }
    
    # Helper methods for backward compatibility
    def _iter_unused_items(self):
        """Iterate over unused items."""
        for item in self.memory_bank:
            item_id = getattr(item, 'id', None)
            if item_id is not None and item_id in self._seen_item_ids:
                continue
            yield item
    
    def _trailing_pause_count(self, history: Sequence[Item | None]) -> int:
        """Count consecutive pauses at the end of history."""
        count = 0
        for i in range(len(history) - 1, -1, -1):
            if is_pause(history[i]):
                count += 1
            else:
                break
        return count
    
    def _calculate_freshness_score(self, i: int, current_item: Item, history: list[Item | None]) -> float:
        """Calculate freshness score for a specific item."""
        if i == 0:
            return 0.0
        if i > 0 and history[i - 1] is not None:
            return 0.0
        
        prior_items = (item for item in history[max(0, i - 6) : i - 1] if item is not None)
        prior_subjects = {s for item in prior_items for s in item.subjects}
        novel_subjects = [s for s in current_item.subjects if s not in prior_subjects]
        return float(len(novel_subjects))
    
    def _calculate_coherence_score(self, i: int, current_item: Item, history: list[Item | None]) -> float:
        """Calculate coherence score for a specific item."""
        context_items = []
        
        # Past up to 3 (stop at pause)
        for j in range(i - 1, max(-1, i - 4), -1):
            if j < 0 or history[j] is None:
                break
            context_items.append(history[j])
        
        # Future side (usually empty at proposal time)
        for j in range(i + 1, min(len(history), i + 4)):
            if history[j] is None:
                break
            context_items.append(history[j])
        
        from collections import Counter
        context_subject_counts = Counter(s for item in context_items for s in item.subjects)
        score = 0.0
        
        if not all(subject in context_subject_counts for subject in current_item.subjects):
            score -= 1.0
        if all(context_subject_counts.get(s, 0) >= 2 for s in current_item.subjects):
            score += 1.0
        
        return score
    
    def _calculate_nonmonotonousness_score(
        self, i: int, current_item: Item, repeated: bool, history: list[Item | None]
    ) -> float:
        """Calculate nonmonotonousness score for a specific item."""
        if repeated:
            return -1.0
        if i < 3:
            return 0.0
        
        last_three_items = [history[j] for j in range(i - 3, i)]
        if all(
            item is not None and any(s in item.subjects for s in current_item.subjects)
            for item in last_three_items
        ):
            return -1.0
        return 0.0