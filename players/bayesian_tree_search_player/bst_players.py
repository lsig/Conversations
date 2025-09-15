from models.player import PlayerSnapshot
from players.bayesian_tree_search_player.bst_player_presets import BayesianTreeBeamSearchPlayer

# Global threshold for all presets
GLOBAL_BST_THRESHOLD = 0.0
GLOBAL_COMPETITION_RATE = 0.5


class BayesTreeBeamLow(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int, competition_rate: float = GLOBAL_COMPETITION_RATE) -> None:
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=competition_rate,
			depth=2,
			breadth=4,
			threhold=GLOBAL_BST_THRESHOLD,
		)
  

class BayesTreeBeamMedium(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int, competition_rate: float = GLOBAL_COMPETITION_RATE) -> None:
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=competition_rate,
			depth=3,
			breadth=16,
			threhold=GLOBAL_BST_THRESHOLD,
		)
  
class BayesTreeBeamHigh(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int, competition_rate: float = GLOBAL_COMPETITION_RATE) -> None:
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=competition_rate,
			depth=6,
			breadth=128,
			threhold=GLOBAL_BST_THRESHOLD,
		)
  

class BayesTreeDynamicStandard(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int, competition_rate: float = GLOBAL_COMPETITION_RATE) -> None:
		# breadth = 4 * |B|
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=competition_rate,
			depth=3,
			breadth_rate=0.5,
			threhold=GLOBAL_BST_THRESHOLD,
		)
  
  
class BayesTreeDynamicWidth(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int, competition_rate: float = GLOBAL_COMPETITION_RATE) -> None:
		# breadth = 4 * |B|
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=competition_rate,
			depth=3,
			breadth_rate=4,
			threhold=GLOBAL_BST_THRESHOLD,
		)


class BayesTreeDynamicDepth(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int, competition_rate: float = GLOBAL_COMPETITION_RATE) -> None:
		# breadth = 4 * |B|
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=competition_rate,
			depth=6,
			breadth_rate=0.5,
			threhold=GLOBAL_BST_THRESHOLD,
		)


class BayesTreeDynamicHigh(BayesianTreeBeamSearchPlayer):
	def __init__(self, snapshot: PlayerSnapshot, conversation_length: int, competition_rate: float = GLOBAL_COMPETITION_RATE) -> None:
		# breadth = 4 * |B|
		super().__init__(
			snapshot=snapshot,
			conversation_length=conversation_length,
			competition_rate=competition_rate,
			depth=6,
			breadth_rate=8,
			threhold=GLOBAL_BST_THRESHOLD,
		)
