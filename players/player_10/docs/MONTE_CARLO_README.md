### Monte Carlo Simulation Framework (Player10)

This document defines: parameters, CLI usage (run + analyze), and the mechanism.

### Parameters (by name)
- Test identity:
  - `--name <str>`: test label (required unless `--predefined`)
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
  - `--output-dir <dir>` (default simulation_results)
  - `--no-save`: do not write results JSON
  - `--quiet`: suppress progress

### CLI usage
- Run: `python -m players.player_10.tools.flex [--predefined ... | --name ...] [params]`
- Analyze: `python -m players.player_10.tools.analyze <results.json> [--analysis] [--plot {altruism,heatmap,distributions}] [--save <png>]`

Notes
- Results JSON is written to `--output-dir` unless `--no-save` is used.
- For multiple configurations (ranges × players), the runner executes all combinations and persists a single timestamped JSON per run.

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
