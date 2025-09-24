import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product

import numpy as np


# ----------------------------
# Simulation runner
# ----------------------------
def run_simulation(length=100, player='p8', memory_size=None, seed=None, env=None, num_players=10):
	if memory_size is None:
		memory_size = length // 10  # fallback

	cmd = [
		'uv',
		'run',
		'python',
		'main.py',
		'--length',
		str(length),
		'--memory_size',
		str(memory_size),
		'--player',
		player,
		str(num_players),  # use the argument here
	]
	if seed is not None:
		cmd += ['--seed', str(seed)]

	result = subprocess.run(cmd, capture_output=True, text=True, cwd='.', env=env)
	if '{' not in result.stdout:
		raise RuntimeError(
			f'Simulation failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}'
		)

	data = json.loads(result.stdout[result.stdout.index('{') :])
	return data


# ----------------------------
# Worker for a single trial
# ----------------------------
def evaluate_worker(v, memory_size, conv_length, num_players, seed):
	env = dict(os.environ)
	env['PLAYER8_V'] = json.dumps(v.tolist())
	sim = run_simulation(
		length=conv_length,
		player='p8',
		memory_size=memory_size,
		seed=seed,
		env=env,
		num_players=num_players,
	)
	return sim['scores']['shared_score_breakdown']['total']


# ----------------------------
# Evaluate a v vector (parallelized)
# ----------------------------
def evaluate_v(v, memory_size=10, conv_length=100, trials=20, num_players=10, max_workers=None):
	scores = []
	with ProcessPoolExecutor(max_workers=max_workers) as executor:
		futures = [
			executor.submit(evaluate_worker, v, memory_size, conv_length, num_players, i)
			for i in range(trials)
		]
		for f in as_completed(futures):
			scores.append(f.result())
	return np.mean(scores)


def quantize(v, step=0.5, vmin=0, vmax=4):
	v = np.round(v / step) * step
	return np.clip(v, vmin, vmax)


# ----------------------------
# Simulated Annealing optimizer
# ----------------------------
def simulated_annealing(
	initial_v=None,
	memory_size=10,
	conv_length=100,
	trials=20,
	max_iter=50,
	initial_temp=10,
	cooling_rate=0.9,
	perturb_scale=0.5,
	num_players=10,
):
	if initial_v is None:
		initial_v = np.zeros(6)

	current_v = np.array(initial_v)
	current_score = evaluate_v(current_v, memory_size, conv_length, trials, num_players)
	best_v = current_v.copy()
	best_score = current_score
	T = initial_temp

	print(f'Initial score: {current_score:.4f}, initial v: {current_v}')

	for iteration in range(max_iter):
		# Perturb v vector
		new_v = current_v + np.random.normal(0, perturb_scale, size=current_v.shape)
		new_v = quantize(new_v, step=0.5, vmin=-5, vmax=5)  # quantize first
		new_score = evaluate_v(new_v, memory_size, conv_length, trials, num_players)

		# Accept new v if better or probabilistically
		if new_score > current_score or np.random.rand() < np.exp((new_score - current_score) / T):
			current_v = new_v
			current_score = new_score

			if new_score > best_score:
				best_v = new_v
				best_score = new_score

		# Cool down
		T *= cooling_rate
		print(
			f'Iter {iteration + 1}/{max_iter}: current_score={current_score:.4f}, best_score={best_score:.4f}'
		)

	return best_v, best_score


# ----------------------------
# Tournament-specific helpers
# ----------------------------
def tournament_scenarios():
	players_list = [2, 6, 10, 11, 12, 20, 34]
	conv_lengths = [10, 50, 200, 1000]
	x_factors = [0.5, 1, 1.5, 10]

	scenarios = []
	for n_players in players_list:
		for conv_len in conv_lengths:
			for x in x_factors:
				mem = int(round((conv_len / n_players) * x))
				mem = max(1, mem)  # ensure >= 1
				key = f'{mem}_{conv_len}_{n_players}'
				scenarios.append((key, mem, conv_len, n_players))
	return scenarios


def train_tournament_scenarios(
	output_file='v_lookup_large.json',
	trials_per_eval=200,
	max_iter_per_sa=200,
	initial_temp=20,
	cooling_rate=0.95,
	perturb_scale=0.25,
	checkpoint_interval=1,
):
	# Load or initialize lookup
	if os.path.exists(output_file):
		with open(output_file) as f:
			v_lookup = json.load(f)
	else:
		v_lookup = {}

	scenarios = tournament_scenarios()

	for i, (key, mem, conv_len, n_players) in enumerate(scenarios, 1):
		print(f'[{i}/{len(scenarios)}] Refining {key}...')

		# start from existing if available
		initial_v = None
		if key in v_lookup:
			initial_v = np.array(v_lookup[key])

		try:
			best_v, best_score = simulated_annealing(
				initial_v=initial_v,
				memory_size=mem,
				conv_length=conv_len,
				trials=trials_per_eval,
				max_iter=max_iter_per_sa,
				initial_temp=initial_temp,
				cooling_rate=cooling_rate,
				perturb_scale=perturb_scale,
				num_players=n_players,
			)
			v_lookup[key] = best_v.tolist()
			print(f'  ✅ Done: best_score={best_score:.4f}, v={best_v}')
		except Exception as e:
			print(f'  ❌ Error optimizing {key}: {e}')
			continue

		if i % checkpoint_interval == 0:
			with open(output_file, 'w') as f:
				json.dump(v_lookup, f, indent=2)
			print(f'Checkpoint saved after {i} scenarios')

	# final save
	with open(output_file, 'w') as f:
		json.dump(v_lookup, f, indent=2)
	print('All tournament scenarios refined and saved.')


# ----------------------------
# Large-scale lookup table generation
# ----------------------------
def generate_large_v_lookup(
	memory_sizes,
	conv_lengths,
	num_players_list,
	trials_per_eval=10,
	max_iter_per_sa=30,
	initial_temp=1.0,
	cooling_rate=0.9,
	perturb_scale=0.5,
	checkpoint_interval=50,
	output_file='v_lookup_large.json',
):
	if os.path.exists(output_file):
		with open(output_file) as f:
			v_lookup = json.load(f)
	else:
		v_lookup = {}

	total_combinations = len(memory_sizes) * len(conv_lengths) * len(num_players_list)
	comb_index = 0

	for mem, conv_len, n_players in product(memory_sizes, conv_lengths, num_players_list):
		# --- restrict space ---
		if n_players * mem <= conv_len:
			continue

		key = f'{mem}_{conv_len}_{n_players}'
		comb_index += 1

		if key in v_lookup:
			continue

		# --- try to reuse a neighbor value as starting point ---
		initial_v = None
		neighbor_keys = []
		if mem > 1:
			neighbor_keys.append(f'{mem - 1}_{conv_len}_{n_players}')
		if conv_len > 20:
			neighbor_keys.append(f'{mem}_{conv_len - 20}_{n_players}')
		if n_players > 2:
			neighbor_keys.append(f'{mem}_{conv_len}_{n_players - 1}')

		for nk in neighbor_keys:
			if nk in v_lookup:
				initial_v = np.array(v_lookup[nk])
				break

		print(
			f'[{comb_index}/{total_combinations}] Optimizing v for memory_size={mem}, conv_length={conv_len}, num_players={n_players} (init from {"neighbor" if initial_v is not None else "zeros"})'
		)

		try:
			best_v, best_score = simulated_annealing(
				initial_v=initial_v,
				memory_size=mem,
				conv_length=conv_len,
				trials=trials_per_eval,
				max_iter=max_iter_per_sa,
				initial_temp=initial_temp,
				cooling_rate=cooling_rate,
				perturb_scale=perturb_scale,
				num_players=n_players,
			)
			v_lookup[key] = best_v.tolist()
			print(f'Done: score={best_score:.4f}, v={best_v}')

		except Exception as e:
			print(f'Error optimizing {key}: {e}')
			continue

		if comb_index % checkpoint_interval == 0:
			with open(output_file, 'w') as f:
				json.dump(v_lookup, f, indent=2)
			print(f'Checkpoint saved after {comb_index} combinations')

	with open(output_file, 'w') as f:
		json.dump(v_lookup, f, indent=2)
	print('All combinations processed. Lookup table saved.')


if __name__ == '__main__':
	# === Option 1: Full sweep ===
	memory_sizes = list(range(10, 100))
	conv_lengths = list(range(10, 300, 20))
	num_players_list = list(range(2, 11))

	# generate_large_v_lookup(
	#     memory_sizes,
	#     conv_lengths,
	#     num_players_list,
	#     trials_per_eval=50,
	#     max_iter_per_sa=20,
	#     checkpoint_interval=1,
	#     initial_temp=10
	# )

	# === Option 2: Tournament-focused training ===
	train_tournament_scenarios(
		output_file='v_lookup_large.json',
		trials_per_eval=200,
		max_iter_per_sa=200,
		initial_temp=20,
		cooling_rate=0.95,
		perturb_scale=0.5,
	)
