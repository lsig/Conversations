import argparse
from dataclasses import dataclass

# DEFAULT_PLAYERS = {
# 	'p0': 0,
# 	'p1': 0,
# 	'p2': 0,
# 	'p3': 0,
# 	'p4': 0,
# 	'p5': 0,
# 	'p6': 0,
# 	'p7': 0,
# 	'p8': 0,
# 	'p9': 0,
# 	'p10': 0,
# 	'p11': 0,
# 	'pr': 0,
# 	'pp': 0,
# 	'p_greedy':0, ###
# 	'p_selfless_greedy':0,
# 	'p_selfish_greedy':0
# }



@dataclass
class Settings:
	players: dict[str, int]
	total_players: int
	subjects: int
	memory_size: int
	length: int
	seed: int
	gui: bool
	output_path: str
	test_player: str | None
	rounds: int
	detailed: bool


def settings() -> Settings:
	"""
	Parses command-line arguments and returns a validated Settings object.
	"""
	parser = argparse.ArgumentParser(description='Run a conversation game simulation.')
	parser.add_argument(
		'--player',
		action='append',
		nargs=2,
		metavar=('TYPE', 'COUNT'),
		help='Set the count for a specific player type (e.g., --player p9 50)',
	)
	parser.add_argument('--subjects', type=int, default=20, help='Number of subjects.')
	parser.add_argument(
		'--memory_size', type=int, default=10, help="Size of each player's memory bank."
	)
	parser.add_argument(
		'--length', type=int, default=10, help='Number of turns in the conversation.'
	)
	parser.add_argument(
		'--seed', type=int, default=91, help='Seed for the random number generator.'
	)
	parser.add_argument('--gui', action='store_true', help='Enable GUI')
	parser.add_argument('--output_path', type=str, default='results', help='Output directory for json/txt/csv files')
	parser.add_argument('--test_player', type=str, default=None, help='Player type prefix to mark as test in analysis (e.g., p3)')
	parser.add_argument('--rounds', type=int, default=1, help='Number of rounds (vary seeds) to repeat with same settings')
	parser.add_argument('--detailed', action='store_true', help='If set, write per-round JSON/TXT/CSV; otherwise only final average CSV')


	args = parser.parse_args()

	### delete the naming check... tedious design, 
	
	# player_counts = DEFAULT_PLAYERS.copy()
	# if args.player:
	# 	for player_type, count_str in args.player:
	# 		if player_type in player_counts:
	# 			player_counts[player_type] = int(count_str)
	# 		else:
	# 			print(f"Warning: Unknown player type '{player_type}' ignored.")
	
	###
 
	player_counts = {}
	if args.player:
		for player_type, count_str in args.player:
			player_counts[player_type] = int(count_str)
      

	args_dict = vars(args)
	del args_dict['player']

	return Settings(players=player_counts, total_players=sum(player_counts.values()), **args_dict)
