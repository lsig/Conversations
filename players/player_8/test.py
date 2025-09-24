import json
import subprocess

# import json

# from core.engine import Engine
# from core.utils import CustomEncoder
# from models.cli import settings
# from models.player import Player
# from players.pause_player import PausePlayer
# from players.player_0.player import Player0
# from players.player_1.player import Player1
# from players.player_2.player import Player2
# from players.player_3.player import Player3
# from players.player_4.player import Player4
# from players.player_5.player import Player5
# from players.player_6.player import Player6
# from players.player_7.player import Player7
# from players.player_8.player import Player8
# from players.player_9.player import Player9
# from players.player_10 import Player10
# from players.player_11.player import Player11
# from players.random_pause_player import RandomPausePlayer
# from players.random_player import RandomPlayer
# from ui.gui import run_gui

# def main():
# 	args = settings()

# 	players: list[type[Player]] = (
# 		[RandomPlayer] * args.players['pr']
# 		+ [PausePlayer] * args.players['pp']
# 		+ [RandomPausePlayer] * args.players['prp']
# 		+ [Player0] * args.players['p0']
# 		+ [Player1] * args.players['p1']
# 		+ [Player2] * args.players['p2']
# 		+ [Player3] * args.players['p3']
# 		+ [Player4] * args.players['p4']
# 		+ [Player5] * args.players['p5']
# 		+ [Player6] * args.players['p6']
# 		+ [Player7] * args.players['p7']
# 		+ [Player8] * args.players['p8']
# 		+ [Player9] * args.players['p9']
# 		+ [Player10] * args.players['p10']
# 		+ [Player11] * args.players['p11']
# 	)

# 	engine = Engine(
# 		players=players,
# 		player_count=args.total_players,
# 		subjects=args.subjects,
# 		memory_size=args.memory_size,
# 		conversation_length=args.length,
# 		seed=args.seed,
# 	)

# 	if args.gui:
# 		run_gui(engine)
# 	else:
# 		simulation_results = engine.run(players)
# 		print(json.dumps(simulation_results, indent=2, cls=CustomEncoder))


# if __name__ == '__main__':
# 	main()


def run_simulation(length=100, player='p8', player_count=10, seed=None):
	"""Run simulator once and return parsed JSON."""
	cmd = [
		'uv',
		'run',
		'python',
		'main.py',
		'--length',
		str(length),
		'--memory_size',
		str(length // player_count),
		'--player',
		player,
		str(player_count),
	]
	if seed is not None:
		cmd += ['--seed', str(seed)]

	result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')
	# print(result.stderr)
	data = json.loads(result.stdout[result.stdout.index('{') :])
	return data


for j in range(8, 11):
	if j not in [2, 9]:
		print(
			f'Player {j}: ',
			sum(
				[
					(
						run_simulation(100, player=f'p{j}', seed=i, player_count=10)['scores'][
							'shared_score_breakdown'
						]['total']
					)
					for i in range(0, 100)
				]
			)
			/ 100,
		)
