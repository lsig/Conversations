import argparse
import json

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Parse a JSON file and extract specific keys.')
	parser.add_argument('--file', '-f', required=True, help='Path to the JSON file to parse.')
	parser.add_argument('--length', '-l', type=int, required=True)
	parser.add_argument('--subjects', type=int, required=True)
	parser.add_argument('--memory_size', type=int, required=True)
	parser.add_argument('--seed', type=int, required=True)
	parser.add_argument('--players', '-p', type=int, required=True)

# 	parser = argparse.ArgumentParser(description='Parse a JSON file and extract specific keys.')
# 	parser.add_argument('--file', '-f', required=True, help='Path to the JSON file to parse.')
# 	parser.add_argument('--length', '-l', type=int)
# 	parser.add_argument('--players', '-p', type=int)
	args = parser.parse_args()

	with open(args.file) as f:
		data = json.load(f)

	# Build id -> name map from speakers (covers RandomPlayer, PausePlayer, etc.)
	id_to_name = {}
	for turn in range(min(args.length, len(data.get('turn_impact', [])))):
		turn_data = data['turn_impact'][turn]
		pid = turn_data.get('speaker_id')
		pname = turn_data.get('speaker_name')
		if pid is not None and pname:
			id_to_name[pid] = pname

	# Identify Player2's UUID if present among speakers
	player_id = None
	for turn in range(min(args.length, len(data.get('turn_impact', [])))):
		turn_data = data['turn_impact'][turn]
		if turn_data.get('speaker_name') == 'Player2':
			player_id = turn_data.get('speaker_id')

	our_final_score = None
	all_totals = []
	player_scores = data['scores']['player_scores']
	for p in range(min(args.players, len(player_scores))):
		entry = player_scores[p]
		curr_player_id = entry['id']
		scores = entry['scores']
		all_totals.append(scores['total'])
		if player_id is not None and curr_player_id == player_id:
			our_final_score = scores

	# Build rankings for all players by total desc (1-based indices). Break ties by lower index
	indexed_totals = list(enumerate(all_totals, start=1))
	# Labels per index: "idx:Name" where Name from id_to_name if known, else fallback
	labels = {}
	for idx, _total in indexed_totals:
		pid = player_scores[idx - 1]['id']
		short_id = str(pid)[-6:] if pid else str(idx)
		name = id_to_name.get(pid, f'Unknown-{short_id}')
		labels[idx] = f'{name}'

	# Sort by total desc, then by index asc to break ties deterministically
	sorted_indices = [idx for idx, _ in sorted(indexed_totals, key=lambda x: (-x[1], x[0]))]
	rankings_str = '>'.join(labels[idx] for idx in sorted_indices)

	# Fallback if Player2 never spoke: choose empty values
	if our_final_score is None:
		our_total = ''
		our_shared = ''
		our_individual = ''
	else:
		our_total = our_final_score['total']
		our_shared = our_final_score['shared']
		our_individual = our_final_score['individual']

	print(f"{args.length},{args.subjects},{args.memory_size},{args.seed},{args.players},{our_total},{our_shared},{our_individual},{rankings_str}")
# 	for turn in range(args.length):
# 		turn_data = data['turn_impact'][turn]
# 		if turn_data['speaker_name'] == 'Player2':
# 			player_id = turn_data['speaker_id']

# 	for p in range(args.players):
# 		curr_player_id = data['scores']['player_scores'][p]['id']
# 		if curr_player_id == player_id:
# 			our_final_score = data['scores']['player_scores'][p]['scores']

# 	print(our_final_score['total'], our_final_score['shared'], our_final_score['individual'])
