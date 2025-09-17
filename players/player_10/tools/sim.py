"""Short CLI alias for the legacy batch simulation runner.

Usage:
  python -m players.player_10.tools.sim --test quick --simulations 10
"""

from .run_simulations import main

if __name__ == "__main__":
    main()


