from __future__ import annotations

import os
import random
from collections.abc import Iterator
from typing import Any

import pandas as pd

from core.engine import Engine
from models.cli import settings
from models.player import Player
from players.player_1.player import Player1
from players.random_pause_player import RandomPausePlayer
from players.random_player import RandomPlayer

# -------- Config --------
STEP: float = 0.1  # grid step (must evenly divide 1.0)
OUTPUT_XLSX: str = 'weights_sweep_results.xlsx'
BASE_SEED: int = 1337


# -------- Simplex grid (sum=1) --------
def generate_simplex_grid(step: float, dims: int = 5) -> Iterator[tuple[float, ...]]:
	if step <= 0 or step > 1:
		raise ValueError('STEP must be in (0,1].')
	N = round(1.0 / step)
	if abs(N * step - 1.0) > 1e-9:
		raise ValueError(f'STEP must evenly divide 1.0 (got {step}).')

	def rec(prefix, remain, slots):
		if slots == 1:
			yield prefix + [remain]
			return
		for k in range(remain + 1):
			yield from rec(prefix + [k], remain - k, slots - 1)

	for ks in rec([], N, dims):
		yield tuple(k * step for k in ks)


# -------- Only Player1 and RandomPlayers --------
def build_players_list(args) -> list[type[Player]]:
	"""Only include Player1 and RandomPlayers; ignore everything else."""
	return (
		[RandomPlayer] * args.players['pr']
		+ [Player1] * args.players['p1']
		+ [RandomPausePlayer] * args.players['prp']
	)


# -------- Run one game for one weight vector --------
def run_once_with_weights(
	args, weights: tuple[float, float, float, float, float], seed_offset: int
) -> dict[str, Any]:
	players_types = build_players_list(args)

	# Stable seed per run
	run_seed = (args.seed if getattr(args, 'seed', None) is not None else BASE_SEED) + seed_offset
	random.seed(run_seed)

	engine = Engine(
		players=players_types,
		player_count=args.total_players,
		subjects=args.subjects,
		memory_size=args.memory_size,
		conversation_length=args.length,
		seed=run_seed,
	)

	# Inject weights into all Player1 instances
	w_coh, w_imp, w_pref, w_nonmon, w_fresh = weights
	for p in engine.players:
		if isinstance(p, Player1):
			p.w_coh, p.w_imp, p.w_pref, p.w_nonmon, p.w_fresh = (
				w_coh,
				w_imp,
				w_pref,
				w_nonmon,
				w_fresh,
			)

	# Run a single simulation
	output = engine.run(players_types)

	# Shared score: same value GUI shows in the "Shared Score" column (per player row)
	shared_total = float(output['scores']['shared_score_breakdown']['total'])

	# Find Player1's individual score (GUI's "Individual Score" for Player1)
	p1_ids = [uid for uid, name in engine.player_names.items() if name == 'Player1']
	p1_individual = float('nan')
	for snap in output['scores']['player_scores']:
		if snap['id'] in p1_ids:
			p1_individual = float(snap['scores']['individual'])
			break  # if multiple Player1s, this takes the first; adjust if you need mean/max

	return {
		'weights': weights,
		'shared_total': shared_total,
		'player1_individual': p1_individual,
	}


# -------- Sweep & write Excel --------
def sweep_and_export(args):
	rows: list[dict[str, float]] = []
	for idx, weights in enumerate(generate_simplex_grid(STEP, dims=5), start=1):
		metrics = run_once_with_weights(args, weights, seed_offset=idx * 1000)
		rows.append(
			{
				'w_coh': metrics['weights'][0],
				'w_imp': metrics['weights'][1],
				'w_pref': metrics['weights'][2],
				'w_nonmon': metrics['weights'][3],
				'w_fresh': metrics['weights'][4],
				'shared_total': metrics['shared_total'],
				'player1_individual': metrics['player1_individual'],
			}
		)

	df = pd.DataFrame(rows)

	# Sort by shared_total then Player1 individual (desc)
	df = df.sort_values(['shared_total', 'player1_individual'], ascending=False).reset_index(
		drop=True
	)

	# Write Excel (xlsxwriter preferred; fallback to openpyxl if needed)
	try:
		with pd.ExcelWriter(OUTPUT_XLSX, engine='xlsxwriter') as xlw:
			df.to_excel(xlw, index=False, sheet_name='results')
	except Exception:
		with pd.ExcelWriter(OUTPUT_XLSX, engine='openpyxl') as xlw:
			df.to_excel(xlw, index=False, sheet_name='results')

	print(f'✅ Wrote {len(df)} rows to {os.path.abspath(OUTPUT_XLSX)}')


def main():
	# Use your existing CLI (same as main.py)
	args = settings()
	# sanity: ensure we actually have Player1 present
	if args.players['p1'] == 0:
		print("⚠️  No Player1 included (--player p1 N). 'player1_individual' will be NaN.")
	sweep_and_export(args)


if __name__ == '__main__':
	main()
