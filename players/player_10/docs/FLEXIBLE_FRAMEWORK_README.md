### Flexible Monte Carlo Framework (Player10)

Run Monte Carlo studies for Player10 with one unified CLI and a small Python API. This guide is intentionally terse and complete.

### One CLI (recommended)
- Run predefined altruism comparison:
  - `python -m players.player_10.tools.flex --predefined altruism`
- Run a custom test (name + ranges):
  - `python -m players.player_10.tools.flex --name my_test --altruism 0.0 0.5 1.0 --simulations 50`
- Random opponents example:
  - `python -m players.player_10.tools.flex --name random_test --players '{"p10": 10, "pr": 5}' --altruism 0.0 0.5 1.0`

Key options (most-used)
- `--predefined {altruism,random2,random5,random10,scalability,parameter_sweep,mixed}`
- or `--name <str>` to define a custom test
- Ranges: `--altruism ...`, `--tau ...`, `--epsilon-fresh ...`, `--epsilon-mono ...`
- Players (JSON strings): `--players '{"p10": 10}' '{"p10": 10, "pr": 2}' ...`
- Controls: `--simulations <int>`, `--conversation-length <int>`, `--subjects <int>`, `--memory-size <int>`
- Output: `--output-dir <dir>`, `--no-save`, `--quiet`

### Python API (minimal)
```python
from players.player_10.sim.test_framework import TestBuilder, FlexibleTestRunner

config = (TestBuilder("my_test")
          .altruism_range([0.0, 0.5, 1.0])
          .player_configs([{'p10': 10}])
          .simulations(50)
          .conversation_length(50)
          .build())

runner = FlexibleTestRunner()
results = runner.run_test(config)
```

### Analyze results
- CLI: `python -m players.player_10.tools.analyze <results.json> --analysis --plot altruism`
- Python:
  ```python
  from players.player_10.analysis import ResultsAnalyzer
  analyzer = ResultsAnalyzer("results.json")
  analyzer.print_detailed_analysis()
  ```

### Presets and examples
- Presets are available via `--predefined ...` (see options above).
- More examples: `players/player_10/examples/` (kept concise: `example_usage.py`).

### Migration
- Use only: `python -m players.player_10.tools.flex ...`.
- Removed legacy runners: `tools.sim`, `tools.run_simulations`, `tools.comprehensive_runner`.
- Internals live under `players/player_10/sim` and `players/player_10/analysis`.
