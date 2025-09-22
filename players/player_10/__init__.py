from .rl.eval_player import EvalPlayer, create_eval_player  # RL evaluation player

# Use the trained RL model as Player10
Player10 = EvalPlayer

__all__ = [
	'Player10',
	'EvalPlayer',
	'create_eval_player',
]
