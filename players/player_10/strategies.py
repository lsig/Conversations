"""
Decision strategies for Player10.

This module contains both the original strategy and the new altruism strategy,
along with special case handlers for different game situations.
"""

import random
import uuid
from collections.abc import Iterable, Sequence
from typing import Optional

from models.item import Item

# Import config module instead of specific values to allow dynamic updates
from . import config as config_module
from .scoring import (
    PlayerPerformanceTracker,
    calculate_canonical_delta,
    is_pause,
    is_repeated,
    subjects_of,
)
from .utils import (
    calculate_selection_weights,
    get_contribution_counts,
    iter_unused_items,
    last_was_pause,
    pick_safe_keepalive_item,
    subjects_in_last_n_nonpause_before_index,
    trailing_pause_count,
)
from .debug_utils import DebugLogger


class OriginalStrategy:
    """
    The original Player10 strategy without altruism.
    """
    
    def __init__(self, player):
        self.player = player
    
    def propose_item(self, history: Sequence[Item | None]) -> Optional[Item]:
        """
        Original Player10 decision logic.
        """
        # Update seen repeats cache
        self._refresh_seen_ids(history)
        
        # Turn 0: use opener logic
        if not history:
            return self._pick_first_turn_opener()
        
        # Keepalive if two pauses already
        if trailing_pause_count(history) >= config_module.MAX_CONSECUTIVE_PAUSES:
            return self._pick_safe_keepalive(history)
        
        # Freshness mode: immediately after a pause
        if last_was_pause(history):
            candidate = self._pick_fresh_post_pause(history)
            if candidate is not None:
                return candidate
            # else fall through to general scoring
        
        # Default: general scoring
        return self._general_scoring_best(history)
    
    def _pick_first_turn_opener(self) -> Optional[Item]:
        """Pick the first turn opener item."""
        # Prefer single-subject items
        single_subject = [it for it in self.player.memory_bank if len(subjects_of(it)) == 1]
        pool = single_subject if single_subject else list(self.player.memory_bank)
        
        if not pool:
            return None
        
        max_imp = max(float(getattr(it, 'importance', 0.0)) for it in pool)
        top = [it for it in pool if float(getattr(it, 'importance', 0.0)) == max_imp]
        return random.choice(top)
    
    def _pick_fresh_post_pause(self, history: Sequence[Item | None]) -> Optional[Item]:
        """Pick a fresh item after a pause."""
        recent_subjects = subjects_in_last_n_nonpause_before_index(
            history, idx=len(history) - 1, n=5
        )
        
        best_item = None
        best_key = None  # (novelty_count, importance)
        
        for item in iter_unused_items(self.player.memory_bank, self.player._seen_item_ids):
            subs = subjects_of(item)
            if not subs:
                continue
            
            novelty = sum(1 for s in subs if s not in recent_subjects)
            if novelty == 0:
                continue
            
            key = (novelty, float(getattr(item, 'importance', 0.0)))
            if best_key is None or key > best_key:
                best_item, best_key = item, key
        
        return best_item
    
    def _pick_safe_keepalive(self, history: Sequence[Item | None]) -> Optional[Item]:
        """Pick a safe item to avoid triggering monotony penalty."""
        return pick_safe_keepalive_item(
            self.player.memory_bank, 
            self.player._seen_item_ids, 
            history
        )
    
    def _general_scoring_best(self, history: Sequence[Item | None]) -> Optional[Item]:
        """
        General scoring logic (original Player10 style).
        
        This method uses calculate_canonical_delta from scoring.py, which now correctly
        implements the official coherence rules. The coherence calculation was fixed to:
        - Return -1.0 when no context items are found (e.g., after pauses)
        - Properly handle pause boundaries in the coherence window
        
        OLD BEHAVIOR (INCORRECT - before coherence fix):
        # The old coherence calculation incorrectly returned 0.0 for empty context
        # instead of -1.0, leading to poor coherence scoring and decision-making
        
        NEW BEHAVIOR (CORRECT - after coherence fix):
        # Now uses the fixed calculate_canonical_delta which properly handles:
        # - Pause boundaries (stops at pauses, doesn't extend across them)
        # - Empty context (returns -1.0 penalty instead of 0.0)
        # - Matches official engine behavior exactly
        """
        best_item = None
        best_score = float('-inf')
        
        for item in self.player.memory_bank:
            if is_repeated(item, history):
                continue
            
            turn_idx = len(history)
            score = calculate_canonical_delta(item, turn_idx, history, is_repeated=False)
            
            if score > best_score:
                best_score = score
                best_item = item
        
        # Use average of last scores as threshold
        if hasattr(self.player, 'last_scores') and self.player.last_scores:
            avg_last_score = sum(self.player.last_scores) / len(self.player.last_scores)
            return best_item if best_score >= avg_last_score else None
        
        return best_item if best_score >= 0 else None
    
    def _refresh_seen_ids(self, history: Sequence[Item | None]) -> None:
        """Update seen item IDs from history."""
        for item in history:
            if is_pause(item):
                continue
            item_id = getattr(item, 'id', None)
            if item_id is not None:
                self.player._seen_item_ids.add(item_id)


class AltruismStrategy:
    """
    The new altruism strategy that considers other players' expected performance.
    """
    
    def __init__(self, player, performance_tracker: PlayerPerformanceTracker):
        self.player = player
        self.performance_tracker = performance_tracker
        self.debug_logger = DebugLogger(player.id)
    
    def propose_item(self, history: Sequence[Item | None]) -> Optional[Item]:
        """
        Altruism decision logic with selection-aware comparison.
        """
        # Update seen repeats cache
        self._refresh_seen_ids(history)
        
        # Special cases (same as original)
        if not history:
            return self._pick_first_turn_opener()
        
        if trailing_pause_count(history) >= config_module.MAX_CONSECUTIVE_PAUSES:
            return self._pick_safe_keepalive(history)
        
        if last_was_pause(history):
            candidate = self._pick_fresh_post_pause(history)
            if candidate is not None:
                return candidate
        
        # Altruism gate
        return self._altruism_gate(history)
    
    def _altruism_gate(self, history: Sequence[Item | None]) -> Optional[Item]:
        """
        Apply the altruism gate to decide whether to propose or hold.
        """
        # Find our best item and calculate its delta
        best_item = None
        best_delta = float('-inf')
        
        for item in iter_unused_items(self.player.memory_bank, self.player._seen_item_ids):
            if is_repeated(item, history):
                continue
            
            turn_idx = len(history)
            delta = calculate_canonical_delta(item, turn_idx, history, is_repeated=False)
            
            if delta > best_delta:
                best_delta = delta
                best_item = item
        
        if best_item is None:
            return None
        
        # Calculate selection weights and expected others' delta
        weights = calculate_selection_weights(history, self.player.id)
        expected_others_delta = self._calculate_expected_others_delta(weights)
        
        # Calculate tau with epsilon adjustments
        tau = self._calculate_tau(best_item, history)
        
        # Log altruism gate decision
        threshold = expected_others_delta - tau
        decision = "PROPOSE" if best_delta >= threshold else "HOLD"
        reason = f"Δ_self={best_delta:.3f} {'>=' if best_delta >= threshold else '<'} threshold={threshold:.3f}"
        
        self.debug_logger.log_altruism_gate(best_delta, expected_others_delta, tau, decision, reason)
        
        # Decision: propose if our delta >= expected others - tau
        if best_delta >= threshold:
            return best_item
        else:
            return None
    
    def _calculate_expected_others_delta(self, weights: dict[uuid.UUID, float]) -> float:
        """
        Calculate expected delta of other players weighted by selection probability.
        """
        expected_delta = 0.0
        
        for player_id, weight in weights.items():
            if player_id != self.player.id:
                trusted_mean = self.performance_tracker.get_trusted_mean(player_id)
                expected_delta += weight * trusted_mean
        
        return expected_delta
    
    def _calculate_tau(self, best_item: Item, history: Sequence[Item | None]) -> float:
        """
        Calculate tau with epsilon adjustments based on context.
        """
        tau = config_module.TAU_MARGIN
        
        # Lower tau if last was pause and our best item is fresh
        if last_was_pause(history) and self._is_item_fresh(best_item, history):
            tau -= config_module.EPSILON_FRESH
        
        # Raise tau if our best item would trigger monotony
        if self._would_trigger_monotony(best_item, history):
            tau += config_module.EPSILON_MONO
        
        return tau
    
    def _is_item_fresh(self, item: Item, history: Sequence[Item | None]) -> bool:
        """
        Check if an item would be considered fresh after a pause.
        """
        if not last_was_pause(history):
            return False
        
        recent_subjects = subjects_in_last_n_nonpause_before_index(
            history, idx=len(history) - 1, n=5
        )
        
        item_subjects = set(subjects_of(item))
        novel_subjects = item_subjects - recent_subjects
        
        return len(novel_subjects) > 0
    
    def _would_trigger_monotony(self, item: Item, history: Sequence[Item | None]) -> bool:
        """
        Check if an item would trigger monotony penalty.
        """
        if len(history) < 3:
            return False
        
        # Get last three non-pause items
        last_three_items = []
        count = 0
        for i in range(len(history) - 1, -1, -1):
            if not is_pause(history[i]):
                last_three_items.append(history[i])
                count += 1
                if count >= 3:
                    break
        
        if len(last_three_items) < 3:
            return False
        
        # Check if any subject appears in all three previous items
        item_subjects = set(subjects_of(item))
        for subject in item_subjects:
            if all(subject in subjects_of(prev_item) for prev_item in last_three_items):
                return True
        
        return False
    
    def _pick_first_turn_opener(self) -> Optional[Item]:
        """Same as original strategy."""
        single_subject = [it for it in self.player.memory_bank if len(subjects_of(it)) == 1]
        pool = single_subject if single_subject else list(self.player.memory_bank)
        
        if not pool:
            return None
        
        max_imp = max(float(getattr(it, 'importance', 0.0)) for it in pool)
        top = [it for it in pool if float(getattr(it, 'importance', 0.0)) == max_imp]
        return random.choice(top)
    
    def _pick_fresh_post_pause(self, history: Sequence[Item | None]) -> Optional[Item]:
        """Same as original strategy."""
        recent_subjects = subjects_in_last_n_nonpause_before_index(
            history, idx=len(history) - 1, n=5
        )
        
        best_item = None
        best_key = None
        
        for item in iter_unused_items(self.player.memory_bank, self.player._seen_item_ids):
            subs = subjects_of(item)
            if not subs:
                continue
            
            novelty = sum(1 for s in subs if s not in recent_subjects)
            if novelty == 0:
                continue
            
            key = (novelty, float(getattr(item, 'importance', 0.0)))
            if best_key is None or key > best_key:
                best_item, best_key = item, key
        
        return best_item
    
    def _pick_safe_keepalive(self, history: Sequence[Item | None]) -> Optional[Item]:
        """Same as original strategy."""
        return pick_safe_keepalive_item(
            self.player.memory_bank, 
            self.player._seen_item_ids, 
            history
        )
    
    def _refresh_seen_ids(self, history: Sequence[Item | None]) -> None:
        """Update seen item IDs from history."""
        for item in history:
            if is_pause(item):
                continue
            item_id = getattr(item, 'id', None)
            if item_id is not None:
                self.player._seen_item_ids.add(item_id)
