from .agent.player import Player10Agent  # Agent-based player for comparison

try:
	from .rl.eval_player import EvalPlayer, create_eval_player  # RL evaluation player
except Exception:  # pragma: no cover - optional dependency
	EvalPlayer = None

	def create_eval_player(*_args, **_kwargs):
		message = (
			'Player10 RL evaluation requires the optional torch dependency and a trained model. '
			'Install torch and ensure models are available to use EvalPlayer.'
		)
		raise RuntimeError(message)


# Use the original Player10Agent as Player10 by default (instead of EvalPlayer)
Player10 = Player10Agent

__all__ = [
	'Player10',
	'EvalPlayer',
	'create_eval_player',
	'Player10Agent',
]
