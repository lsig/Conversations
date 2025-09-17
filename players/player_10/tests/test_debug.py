"""
Test script to demonstrate Player10 debug functionality.

This script shows how to enable debug logging and see the decision-making process.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from players.player_10.agent.config import DEBUG_ENABLED, DEBUG_LEVEL
from players.player_10 import Player10
from models.item import Item
from models.player import PlayerSnapshot, GameContext
import uuid

def test_debug_functionality():
    """Test Player10 with debug logging enabled."""
    
    # Enable debug logging
    import players.player_10.config as config_module
    config_module.DEBUG_ENABLED = True
    config_module.DEBUG_LEVEL = 2  # Detailed logging
    
    print("=== PLAYER10 DEBUG TEST ===")
    print("Debug logging enabled with level 2 (detailed)")
    print("=" * 50)
    
    # Create Player10 instance using proper constructor
    subjects = ["science", "technology", "art", "music", "sports"]
    snapshot = PlayerSnapshot(
        id=uuid.uuid4(),
        preferences=(0, 1, 2, 3, 4),  # Indices for subjects
        memory_bank=()
    )
    ctx = GameContext(number_of_players=1, conversation_length=50)
    player = Player10(snapshot, ctx)
    
    # Create some sample items for the memory bank
    sample_items = [
        Item(id=uuid.uuid4(), subjects=(0, 1), importance=0.8, player_id=uuid.uuid4()),
        Item(id=uuid.uuid4(), subjects=(3, 0), importance=0.7, player_id=uuid.uuid4()),
        Item(id=uuid.uuid4(), subjects=(2,), importance=0.6, player_id=uuid.uuid4()),
        Item(id=uuid.uuid4(), subjects=(0, 1), importance=0.9, player_id=uuid.uuid4()),
        Item(id=uuid.uuid4(), subjects=(4, 0), importance=0.5, player_id=uuid.uuid4()),
    ]
    
    # Add items to memory bank (convert to list first)
    player.memory_bank = list(player.memory_bank)
    for item in sample_items:
        player.memory_bank.append(item)
    
    print(f"Created Player10 with {len(player.memory_bank)} items in memory bank")
    print(f"Subjects: {subjects}")
    print()
    
    # Simulate a few turns
    history = []
    
    for turn in range(1, 4):
        print(f"\n{'='*60}")
        print(f"TURN {turn} - MAKING DECISION")
        print(f"{'='*60}")
        
        # Player10 makes a decision
        decision = player.propose_item(history)
        
        if decision:
            print(f"\nPlayer10 decided to propose: Item(id={decision.id})")
            # Add the decision to history
            history.append(decision)
        else:
            print(f"\nPlayer10 decided to PASS")
            history.append(None)  # Pause
    
    print(f"\n{'='*60}")
    print("DEBUG TEST COMPLETED")
    print(f"{'='*60}")
    print(f"Final history length: {len(history)}")
    print(f"Items proposed: {sum(1 for item in history if item is not None)}")
    print(f"Pauses: {sum(1 for item in history if item is None)}")

if __name__ == "__main__":
    test_debug_functionality()
