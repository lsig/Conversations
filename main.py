import json

from core.engine import Engine
from core.utils import CustomEncoder
from core.utils import ConversationAnalyzer
from models.cli import settings
from ui.gui import run_gui

from models.player import Player
from players.pause_player import PausePlayer
from players.random_player import RandomPlayer
from players.zipper_player.player import ZipperPlayer
from players.player_3.player import Player3

from players.bayesian_tree_search_player.greedy_players import BalancedGreedyPlayer, SelflessGreedyPlayer, SelfishGreedyPlayer
from players.bayesian_tree_search_player.bst_players import BayesTreeBeamLow, BayesTreeBeamMedium, BayesTreeBeamHigh, BayesTreeDynamicStandard, BayesTreeDynamicWidth


### add the mapping here when adding new players. 
g_player_classes = {
		'pr': RandomPlayer,
		'pp': PausePlayer,
  
		# Final Player to present.
		'p3': Player3,
  
		# zipper player
		'p_zipper': ZipperPlayer,
  
		# greedy players
		'p_balanced_greedy': BalancedGreedyPlayer,
		'p_selfless_greedy': SelflessGreedyPlayer,
		'p_selfish_greedy': SelfishGreedyPlayer,
		
		# bayesian tree + beam search player (different efforts) | balanced competition + no threhold. 
		'p_bst_low': BayesTreeBeamLow,
		'p_bst_medium': BayesTreeBeamMedium,
		'p_bst_high': BayesTreeBeamHigh,
		'p_bst_dynamic': BayesTreeDynamicStandard,
		'p_bst_dynamic_width': BayesTreeDynamicWidth,
		'p_bst_dynamic_depth': BayesTreeDynamicWidth
	}

def main():
	args = settings()

	# Build players list using the mapping
	players: list[type[Player]] = []
	for player_name, count in args.players.items():
		if player_name in g_player_classes:
			players.extend([g_player_classes[player_name]] * count)

	import os
	analyzer = ConversationAnalyzer()

	# Minimal CLI output: settings and players
	print(f"Settings: length={args.length}, memory_size={args.memory_size}, subjects={args.subjects}, rounds={args.rounds}, detailed={args.detailed}")
	print(f"Players: {args.players}")

	if args.gui:
		engine = Engine(
			players=players,
			player_count=args.total_players,
			subjects=args.subjects,
			memory_size=args.memory_size,
			conversation_length=args.length,
			seed=args.seed,
		)
		run_gui(engine)
	else:
		os.makedirs(args.output_path or 'results', exist_ok=True)

		# tqdm progress if available and multiple rounds
		try:
			from tqdm import trange as _trange
		except Exception:
			_trange = None

		per_type_sums: dict[str, dict[str, float]] = {}
		per_type_counts: dict[str, int] = {}

		rounds = max(1, args.rounds)
		base_seed = args.seed
		if _trange is None and rounds > 1:
			print(f"Rounds: {rounds}")

		for r in (range(rounds) if _trange is None or rounds <= 1 else _trange(rounds)):
			seed = base_seed + r
			engine = Engine(
				players=players,
				player_count=args.total_players,
				subjects=args.subjects,
				memory_size=args.memory_size,
				conversation_length=args.length,
				seed=seed,
			)
			simulation_results = engine.run(players)

			# Per-type rows for this round
			rows = analyzer.compute_type_averages(simulation_results, engine=engine)
			for row in rows:
				type_name = row['type']
				if type_name not in per_type_sums:
					per_type_sums[type_name] = {
						'avg_score': 0.0,
						'individual': 0.0,
						'avg_shared_score': 0.0,
						'avg_contributed_shared_score': 0.0,
						'avg_involvement_ratio': 0.0,
						'importance': 0.0,
						'coherence': 0.0,
						'freshness': 0.0,
						'nonmonotone': 0.0,
						'player_numbers': 0,
					}
				per_type_counts[type_name] = per_type_counts.get(type_name, 0) + 1
				acc = per_type_sums[type_name]
				if not acc['player_numbers']:
					acc['player_numbers'] = int(row.get('player_numbers', 0))
				acc['avg_score'] += float(row['score'])
				acc['individual'] += float(row['individual'])
				acc['avg_shared_score'] += float(row['shared_score'])
				acc['avg_contributed_shared_score'] += float(row['contributed_shared_score'])
				acc['avg_involvement_ratio'] += float(row['involvement_ratio'])
				# capture contributed individual per round as well if present
				if 'contributed_individual_score' in row:
					acc['contributed_individual_score'] = acc.get('contributed_individual_score', 0.0) + float(row['contributed_individual_score'])
				acc['importance'] += float(row['importance'])
				acc['coherence'] += float(row['coherence'])
				acc['freshness'] += float(row['freshness'])
				acc['nonmonotone'] += float(row['nonmonotone'])

			if args.detailed:
				round_dir = os.path.join(args.output_path, f'round_{r+1}')
				os.makedirs(round_dir, exist_ok=True)
				# JSON
				json_path = os.path.join(round_dir, 'simulation_results.json')
				with open(json_path, 'w') as f:
					json.dump(simulation_results, f, cls=CustomEncoder, indent=2)
				# TXT
				text = analyzer.raw_data_to_human_readable(simulation_results, engine=engine, test_player=args.test_player)
				txt_path = os.path.join(round_dir, 'analysis.txt')
				with open(txt_path, 'w') as f:
					f.write(text)
				# CSV per round
				csv_path = os.path.join(round_dir, 'player_metrics.csv')
				analyzer.raw_data_to_csv(simulation_results, engine=engine, test_player=args.test_player, csv_path=csv_path)

		# Final per-type averages across rounds → results.csv (same schema as per-round player_metrics.csv)
		final_rows = []
		for type_name, sums in per_type_sums.items():
			cnt = max(1, per_type_counts.get(type_name, 1))
			final_rows.append({
				'type': type_name,
				'player_numbers': int(sums.get('player_numbers', 0)),
				'score': sums['avg_score'] / cnt,
				'individual': sums.get('individual', 0.0) / cnt if 'individual' in sums else 0.0,
				'shared_score': sums['avg_shared_score'] / cnt,
				'contributed_individual_score': sums.get('contributed_individual_score', 0.0) / cnt,
				'contributed_shared_score': sums['avg_contributed_shared_score'] / cnt,
				'involvement_ratio': sums['avg_involvement_ratio'] / cnt,
				'importance': sums['importance'] / cnt,
				'coherence': sums['coherence'] / cnt,
				'freshness': sums['freshness'] / cnt,
				'nonmonotone': sums['nonmonotone'] / cnt,
			})
		# Sort by score desc
		final_rows.sort(key=lambda r: r['score'], reverse=True)
		results_csv = os.path.join(args.output_path, 'results.csv')
		with open(results_csv, 'w', newline='') as f:
			f.write('type,player_numbers,score,individual,shared_score,involvement_ratio,contributed_individual_score,contributed_shared_score,importance,coherence,freshness,nonmonotone\n')
			for r in final_rows:
				f.write(f"{r['type']},{r.get('player_numbers',0)},{r['score']:.2f},{r['individual']:.2f},{r['shared_score']:.2f},{r['involvement_ratio']:.2f},{r.get('contributed_individual_score',0.0):.2f},{r['contributed_shared_score']:.2f},{r['importance']:.2f},{r['coherence']:.2f},{r['freshness']:.2f},{r['nonmonotone']:.2f}\n")
	

if __name__ == '__main__':
	main()
