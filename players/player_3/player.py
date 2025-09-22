from players.player_3.bst_player_presets import BayesianTreeBeamSearchPlayer
from models.player import GameContext, Item, Player, PlayerSnapshot

class Player3(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, ctx: GameContext) -> None:
		# initial_competition_rate=0.5 (balanced), depth=1, width/breadth inferred from memory bank length
		super().__init__(
			snapshot=snapshot,
			ctx=ctx,
			initial_competition_rate=0.5,
			depth=1,
			breadth=None,
			static_threhold=0.5
		)
