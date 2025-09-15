from models.player import PlayerSnapshot
from players.player_3.bst_player_presets import BayesianTreeBeamSearchPlayer

# Global threshold for all presets
GLOBAL_BST_THRESHOLD = 0.5


# 0913 version: just the simple greedy player with balanced scoring.
class Player3(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:
		# competition_rate=0.5 (balanced), depth=1, width/breadth inferred from memory bank length
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=0.5,
			depth=1,
			breadth=None,
			threhold=GLOBAL_BST_THRESHOLD,
		)