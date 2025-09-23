import json
import random

import numpy as np

from core.engine import Engine
from core.utils import CustomEncoder
from models.cli import settings
from models.player import Player
from players.pause_player import PausePlayer
from players.player_0.player import Player0
from players.player_1.player import Player1
from players.player_2.player import Player2
from players.player_3.player import Player3
from players.player_4.player import Player4
from players.player_5.player import Player5
from players.player_6.player import Player6
from players.player_7.player import Player7
from players.player_8.player import Player8
from players.player_9.player import Player9
from players.player_10.player import Player10
from players.player_11.player import Player11
from players.random_pause_player import RandomPausePlayer
from players.random_player import RandomPlayer
from ui.gui import run_gui


def main():
	args = settings()
	random.seed(args.seed)
	np.random.seed(args.seed)

	players: list[type[Player]] = (
		[RandomPlayer] * args.players['pr']
		+ [PausePlayer] * args.players['pp']
		+ [RandomPausePlayer] * args.players['prp']
		+ [Player0] * args.players['p0']
		+ [Player1] * args.players['p1']
		+ [Player2] * args.players['p2']
		+ [Player3] * args.players['p3']
		+ [Player4] * args.players['p4']
		+ [Player5] * args.players['p5']
		+ [Player6] * args.players['p6']
		+ [Player7] * args.players['p7']
		+ [Player8] * args.players['p8']
		+ [Player9] * args.players['p9']
		+ [Player10] * args.players['p10']
		+ [Player11] * args.players['p11']
	)

	engine = Engine(
		players=players,
		player_count=args.total_players,
		subjects=args.subjects,
		memory_size=args.memory_size,
		conversation_length=args.length,
	)

	if args.gui:
		run_gui(engine)
	else:
		simulation_results = engine.run(players)
		print(json.dumps(simulation_results, indent=2, cls=CustomEncoder))


if __name__ == '__main__':
	main()
