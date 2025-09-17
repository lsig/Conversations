"""
Quick debug test to show debug output in console.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from players.player_10.agent.config import DEBUG_ENABLED, DEBUG_LEVEL
from players.player_10 import Player10
from models.item import Item
from models.player import PlayerSnapshot, GameContext
import uuid

def quick_debug_test():
    """Quick test to show debug output."""
    
    print("=== QUICK DEBUG TEST ===")
    print(f"Debug enabled: {DEBUG_ENABLED}")
    print(f"Debug level: {DEBUG_LEVEL}")
    print("=" * 40)
    
    # Create Player10 instance
    subjects = ["science", "technology", "art", "music", "sports"]
    snapshot = PlayerSnapshot(
        id=uuid.uuid4(),
        preferences=(0, 1, 2, 3, 4),
        memory_bank=()
    )
    ctx = GameContext(number_of_players=1, conversation_length=50)
    player = Player10(snapshot, ctx)
    
    # Add some items to memory bank
    sample_items = [
        Item(id=uuid.uuid4(), subjects=(0, 1), importance=0.8, player_id=uuid.uuid4()),
        Item(id=uuid.uuid4(), subjects=(3, 0), importance=0.7, player_id=uuid.uuid4()),
        Item(id=uuid.uuid4(), subjects=(2,), importance=0.6, player_id=uuid.uuid4()),
    ]
    
    player.memory_bank = list(player.memory_bank)
    for item in sample_items:
        player.memory_bank.append(item)
    
    print(f"Created Player10 with {len(player.memory_bank)} items")
    print()
    
    # Run a few turns
    history = []
    for turn in range(1, 4):
        print(f"--- TURN {turn} ---")
        decision = player.propose_item(history)
        
        if decision:
            print(f"DECISION: Proposed Item(id={decision.id})")
            history.append(decision)
        else:
            print(f"DECISION: PASSED")
            history.append(None)
        print()
    
    print("=== TEST COMPLETED ===")

if __name__ == "__main__":
    quick_debug_test()
