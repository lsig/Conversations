import argparse
import json

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Parse a JSON file and extract specific keys.')
	parser.add_argument('--file', '-f', required=True, help='Path to the JSON file to parse.')
	parser.add_argument('--length', '-l', type=int)
	parser.add_argument('--players', '-p', type=int)
	args = parser.parse_args()

	with open(args.file) as f:
		data = json.load(f)

	for turn in range(args.length):
		turn_data = data['turn_impact'][turn]
		if turn_data['speaker_name'] == 'Player2':
			player_id = turn_data['speaker_id']

	for p in range(args.players):
		curr_player_id = data['scores']['player_scores'][p]['id']
		if curr_player_id == player_id:
			our_final_score = data['scores']['player_scores'][p]['scores']

	print(our_final_score['total'], our_final_score['shared'], our_final_score['individual'])
