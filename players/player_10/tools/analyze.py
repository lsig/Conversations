"""
Thin CLI wrapper to run analysis from the library module.

Usage:
  python -m players.player_10.tools.analyze path/to/results.json --plot altruism --analysis
"""

from ..analysis.analyze_results import main

if __name__ == "__main__":
    main()


