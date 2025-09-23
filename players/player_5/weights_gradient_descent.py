import json
import random
import subprocess


def run_and_parse(
	weights,
	args,
	learning_rate=0.01,
):
	p = subprocess.run(['uv', 'run', 'python', 'main.py'] + args, stdout=subprocess.PIPE, text=True)

	# split by lines and drop the first two
	lines = p.stdout.splitlines()
	json_str = '\n'.join(lines[2:])  # everything after the pygame banner

	data = json.loads(json_str)

	player_ids = []

	for turn in data['turn_impact']:
		if turn['speaker_name'] == 'Player5':
			player_ids += [turn['speaker_id']]

	if len(player_ids) > 0:
		scores = []

		for player in data['scores']['player_scores']:
			if player['id'] in player_ids:
				scores += [player['scores']['total']]

		return sum(scores) / len(scores)

	else:
		raise ValueError('Player ID not found in the output data.')


def select_players(num_players, available_players=(1, 2, 3, 4, 5, 6, 7, 8, 9), pr=False):
	"""
	Randomly assign num_players slots among a given list of players.
	Guarantee that player 5 gets at least one slot.
	Optionally guarantee 1 slot for 'pr' (random player).

	Args:
	num_players (int): total slots to allocate.
	available_players (list[int]): list of player numbers (e.g. [1,2,3,5,8]).
	pr (bool): whether to include a 'pr' random player.

	Returns:
	list[str]: CLI args like ["--player", "p1", "2", ...].
	"""

	if available_players is None:
		available_players = list(range(1, 11))  # default p1..p10

	# Start with zero allocations
	splits = {p: 0 for p in available_players}

	# Guarantee player 5 gets one if available
	if 5 in splits:
		splits[5] = 1
		remaining = num_players - 1
	else:
		remaining = num_players

	# Guarantee 'pr' if requested
	pr_count = 0
	if pr:
		pr_count = 1
		remaining -= 1

	# Distribute the remaining randomly among available players
	for _ in range(remaining):
		player = random.choice(available_players)
		splits[player] += 1

	# Build CLI args
	args = []
	for p in sorted(splits.keys()):
		args.extend(['--player', f'p{p}', str(splits[p])])

	if pr:
		args.extend(['--player', 'pr', str(pr_count)])

	return args


def get_score_avg(cmd, num_players):
	# Run multiple times and average results
	cmd_rand = cmd + select_players(num_players, pr=True)
	cmd_other = cmd + select_players(num_players, pr=False)
	cmd_self = cmd + ['--player', 'p5', str(num_players)]

	cmds = [cmd_rand, cmd_other, cmd_self]

	for c in cmds:
		results = [run_and_parse([], c) for c in cmds]

	return results


# create table of optimal weights

results = []
save_every = 20
outfile = 'simulation_results.json'

counter = 0

for length in range(10, 501, 10):
	for players in range(3, length, length // 10):
		for subjects in range(10, length * 2, length // 5):
			for memory in range(5, length, length // 10):
				cmd = [
					'--length',
					str(length),
					'--subjects',
					str(length // 2),
					'--seed',
					str(91),
					'--memory_size',
					str(memory),
					'--subjects',
					str(subjects),
				]

				cmd_test = cmd + ['--player', 'p5', str(players)]
				res = None

				try:
					res = get_score_avg(cmd, num_players=players)

				except Exception as e:
					print(f'Error during simulation: {e}')
					continue
				results.append(
					{
						'length': length,
						'players': players,
						'subjects': subjects,
						'memory': memory,
						'score': res,
					}
				)

				counter += 1

				# Periodically save progress
				if counter % save_every == 0:
					with open(outfile, 'w') as f:
						json.dump(results, f, indent=2)
					print(f'Checkpoint saved at {counter} iterations.')

# Final save at the end
with open(outfile, 'w') as f:
	json.dump(results, f, indent=2)
print('All results saved.')
print(res)
