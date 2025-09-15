from models.player import PlayerSnapshot
from players.bayesian_tree_search_player.bst_player_presets import BayesianTreeBeamSearchPlayer

# Global threshold for all presets
GLOBAL_BST_THRESHOLD = 0.5


class BalancedGreedyPlayer(BayesianTreeBeamSearchPlayer):
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


class SelflessGreedyPlayer(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:
		# competition_rate low (favor shared) e.g., 0, depth=1
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=0,
			depth=1,
			breadth=None,
			threhold=GLOBAL_BST_THRESHOLD,
		)


class SelfishGreedyPlayer(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int) -> None:
		# competition_rate high (favor individual) e.g., 1.0, depth=1
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=1.0,
			depth=1,
			breadth=None,
			threhold=GLOBAL_BST_THRESHOLD,
		)
