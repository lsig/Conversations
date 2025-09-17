"""
Debug toggle utility for Player10.

This script allows you to easily enable/disable debug logging
and set the debug level from the command line.
"""

import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def main():
    parser = argparse.ArgumentParser(description='Toggle Player10 debug logging')
    parser.add_argument('--enable', action='store_true', help='Enable debug logging')
    parser.add_argument('--disable', action='store_true', help='Disable debug logging')
    parser.add_argument('--level', type=int, choices=[1, 2, 3], help='Set debug level (1=basic, 2=detailed, 3=verbose)')
    parser.add_argument('--status', action='store_true', help='Show current debug status')
    
    args = parser.parse_args()
    
    # Import config module
    import players.player_10.config as config_module
    
    if args.status:
        print(f"Current debug status:")
        print(f"  DEBUG_ENABLED: {config_module.DEBUG_ENABLED}")
        print(f"  DEBUG_LEVEL: {config_module.DEBUG_LEVEL}")
        print(f"  DEBUG_STRATEGY_SELECTION: {config_module.DEBUG_STRATEGY_SELECTION}")
        print(f"  DEBUG_ITEM_EVALUATION: {config_module.DEBUG_ITEM_EVALUATION}")
        print(f"  DEBUG_ALTRUISM_GATE: {config_module.DEBUG_ALTRUISM_GATE}")
        print(f"  DEBUG_PERFORMANCE_TRACKING: {config_module.DEBUG_PERFORMANCE_TRACKING}")
        print(f"  DEBUG_SELECTION_FORECAST: {config_module.DEBUG_SELECTION_FORECAST}")
        print(f"  DEBUG_SAFETY_CHECKS: {config_module.DEBUG_SAFETY_CHECKS}")
        return
    
    if args.enable:
        config_module.DEBUG_ENABLED = True
        print("Debug logging ENABLED")
    
    if args.disable:
        config_module.DEBUG_ENABLED = False
        print("Debug logging DISABLED")
    
    if args.level:
        config_module.DEBUG_LEVEL = args.level
        print(f"Debug level set to {args.level}")
    
    # Show final status
    print(f"\nFinal debug status:")
    print(f"  DEBUG_ENABLED: {config_module.DEBUG_ENABLED}")
    print(f"  DEBUG_LEVEL: {config_module.DEBUG_LEVEL}")

if __name__ == "__main__":
    main()
