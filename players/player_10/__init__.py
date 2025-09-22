from .rl.eval_player import EvalPlayer, create_eval_player  # RL evaluation player
from .agent.player import Player10Agent  # Agent-based player for comparison

# Use the trained RL model as Player10 by default
Player10 = EvalPlayer

__all__ = [
	'Player10',
	'EvalPlayer', 
	'create_eval_player',
	'Player10Agent',
]
