from models.player import GameContext, PlayerSnapshot
from players.player_3.bst_player_presets import BayesianTreeBeamSearchPlayer

GLOBAL_COMPETITION_RATE = 0.5


class Player3(BayesianTreeBeamSearchPlayer):
	def __init__(
		self,
		snapshot: PlayerSnapshot,
		ctx: GameContext,
		initial_competition_rate: float = GLOBAL_COMPETITION_RATE,
	) -> None:
		super().__init__(
			snapshot=snapshot,
			ctx=ctx,
			initial_competition_rate=initial_competition_rate,
			depth=3,
			breadth=16,
			# static_threhold=GLOBAL_BST_THREHOLD,
		)
