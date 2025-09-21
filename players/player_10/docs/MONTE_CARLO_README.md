### Monte Carlo Simulation Framework (Player10)

This document defines: parameters, CLI usage (run + analyze), and the mechanism.

### Parameters (by name)
- Test identity:
  - `--name <str>`: optional test label (defaults to an auto-stamped name)
  - `--predefined {altruism,random2,random5,random10,scalability,parameter_sweep,mixed}`
- Ranges:
  - `--altruism <floats...>`: altruism probabilities
  - `--tau <floats...>`: tau margins
  - `--epsilon-fresh <floats...>`: epsilon fresh
  - `--epsilon-mono <floats...>`: epsilon mono
- Players:
  - `--players '<json>' ['<json>' ...]`: one or more JSON player configurations
- Simulation controls:
  - `--simulations <int>`: per-configuration runs (default 50)
  - `--conversation-length <int>` (default 50)
  - `--subjects <int>` (default 20)
  - `--memory-size <int>` (default 10)
  - `--output-dir <dir>` (default `players/player_10/results`)
  - `--no-save`: do not write results JSON
  - `--quiet`: suppress progress

### CLI usage
- Run: `python -m players.player_10.tools.run [--predefined ... | --name ...] [params]`
- Analyze: `python -m players.player_10.tools.analyze <results.json> [--analysis] [--plot {altruism,heatmap,distributions}] [--save <png>]`

Notes
- Parameter defaults mirror the values defined in `players/player_10/agent/config.py` (e.g., `ALTRUISM_USE_PROB`, `TAU_MARGIN`).
- Results JSON is written to `--output-dir` (default `players/player_10/results`) unless `--no-save` is used.
- Filenames are prefixed with the run timestamp, and each JSON now contains a top-level `metadata` block summarizing the configuration (ranges, players, seeds, CLI command) followed by the `results` list.
- For multiple configurations (ranges × players), the runner executes all combinations and persists a single timestamped JSON per run.
 - Strategy descriptions: see `players/player_10/docs/STRATEGIES.md`.

### Why we sweep τ and altruism probability

The altruism gate compares our best Δ against a selection-weighted expectation of others’ learned quality. τ shifts this decision boundary; ε_fresh and ε_mono refine it near pauses and monotony risk. The altruism probability controls how often we use this selection-aware policy versus the original scoring, trading initiative for restraint. Sweeping these parameters shows how conversation quality responds to more/less altruistic speaking behavior.

### Mechanism (concise)
- Flexible runner builds a cartesian product of parameter ranges and player configurations.
- For each combination:
  - Seeds RNG per run; updates Player10 config with the combination’s parameters.
  - Creates players and runs the core `Engine` for the specified conversation length.
  - Records aggregate metrics per run (total score, Player10 score, length, pauses, early termination, unique items, time).
- After all runs:
  - Aggregates by configuration: means, std devs, counts; identifies top configurations.
  - Writes JSON with raw runs and summaries (unless `--no-save`).

### Output
- JSON in `--output-dir` with:
  - per-run results, aggregated summaries, and best configurations.
- Use the analyze CLI to print tables or save plots.
