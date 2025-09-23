import argparse
import json


def main() -> None:
	parser = argparse.ArgumentParser(description='Attach input parameters to a simulation JSON.')
	parser.add_argument('--in', dest='in_path', required=True)
	parser.add_argument('--out', dest='out_path', required=True)
	parser.add_argument('--length', type=int, required=True)
	parser.add_argument('--subjects', type=int, required=True)
	parser.add_argument('--memory_size', type=int, required=True)
	parser.add_argument('--seed', type=int, required=True)
	parser.add_argument('--players', type=int, required=True)
	parser.add_argument('--player_args', type=str, default='')
	args = parser.parse_args()

	with open(args.in_path) as f:
		data = json.load(f)

	data['parameters'] = {
		'length': args.length,
		'subjects': args.subjects,
		'memory_size': args.memory_size,
		'seed': args.seed,
		'players': args.players,
		'player_args': args.player_args,
	}

	with open(args.out_path, 'w') as f:
		json.dump(data, f)


if __name__ == '__main__':
	main()


