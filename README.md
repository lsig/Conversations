# Project 1

### Setup

Start with installing uv, uv is a modern python package manager.

- [UV Install instructions](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

Using brew:
```bash
brew install uv
```

### Running the simulator

```bash
uv run main.py <CLI_ARGS>
```

---

### CLI Arguments

The simulation can be configured using a variety of command-line arguments. If no arguments are provided, the simulation will run with a default set of parameters.

#### General Options

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--gui` | `False` | Launches the graphical user interface to visualize the simulation. If omitted, the simulation runs in the command line and outputs a JSON blob. |
| `--subjects` | `20` | Sets the total number of unique subjects in the simulation. |
| `--memory_size` | `10` | Sets the number of items each player has in their memory bank. |
| `--length` | `10` | Sets the maximum number of turns for the conversation. |
| `--seed` | `91` | Provides a seed for the random number generator to ensure reproducible simulations. |

#### Player Configuration

The `--player` argument allows you to specify the number of players of a certain type to include in the simulation. You can use this argument multiple times to create a mix of different players.

- **Format:** `--player <TYPE> <COUNT>`
- **`<TYPE>`:** A short code representing the player type.
- **`<COUNT>`:** The number of players of that type to add.

##### Available Player Types

| Code | Player Type |
| :--- | :--- |
| `pr` | RandomPlayer |
| `prp` | RandomPausePlayer |
| `pp` | PausePlayer |
| `p0`-`p11` | Player0 through Player11 |

---

### Code Quality and Formatting

The repository uses Ruff for both formatting and linting, if your PR does not pass the CI checks it won't be merged.

VSCode has a Ruff extension that can run on save. [Editor Setup](https://docs.astral.sh/ruff/editors/setup/).

To run formatting check:

```bash
uv run ruff format --check
```

To run formatting:

```bash
uv run ruff format
```

To run linting:

```bash
uv run ruff check
```

To run linting with auto-fix:

```bash
uv run ruff check --fix
```

---

### Usage Examples

Here are some common examples of how to run the simulation with different configurations.

##### Example 1: Run with the GUI

To run the simulation and see the visualizer, use the `--gui` flag. This example also increases the conversation length and adds 10 instances of the random player

```bash
uv run python main.py --gui --length 50 --player pr 10
```

##### Example 2: Run a Simulation with Specific Players

To create a game with 2 `Player0` instances and 8 `RandomPlayer` instances, use the `--player` argument twice.

```bash
uv run python main.py --player p0 2 --player pr 8
```

##### Example 3: Run a CLI Simulation

This example runs a long conversation with 100 turns, a large number of subjects, and a custom seed. Since `--gui` is not specified, it will output the final JSON results to the console.

```bash
uv run python main.py --length 100 --subjects 50 --seed 123 --player p0 10
```

##### Example 4: Run a Head-to-Head Test

To test `Player1` against `Player2` without any other players, specify only those two types.

```bash
uv run python main.py --player p1 1 --player p2 1 --length 20
```

---

### What's New

- **Analysis utilities (`core/utils.py`)**:
  - Added `CustomEncoder` for safe JSON export (handles `Item`, `UUID`, and nested dict keys).
  - Added `ConversationAnalyzer` for per-player and per-type analysis, CSV export, and human-readable reports with consistent float precision.
  - CLI runs can now write:
    - Per-round JSON/TXT/CSV when `--detailed` is set.
    - Final aggregated `results.csv` across `--rounds` in the `--output_path` directory.

- **Bayesian Tree Search players (`players/bayesian_tree_search_player/`)**:
  - `bst_player_presets.py`: Core search data structures and presets
    - `BayesianTree`, `BayesianTreeNode`, and `BayesianTreeBeamSearch` implement a beam search over conversation items. Paths are scored by prior-probability–weighted expectations, normalized along the path; search supports configurable `depth` and `breadth`.
    - `BayesianTreeBeamSearchPlayer`: base player that evaluates with a weighted combination of shared vs individual utility.
    - Presets: `BayesTreeBeamLow`, `BayesTreeBeamMedium`, `BayesTreeBeamHigh`, `BayesTreeDynamicStandard`, `BayesTreeDynamicWidth`, `BayesTreeDynamicDepth`.
  - `utils.py`: `ConversationScorer` that blends shared score (importance, coherence, freshness, nonmonotone, with repeated-item handling) and individual preference bonuses via `competition_rate`.
  - `greedy_players.py`: simple depth-1 greedy variants
    - `BalancedGreedyPlayer` (`competition_rate=0.5`)
    - `SelflessGreedyPlayer` (`competition_rate=0.0`)
    - `SelfishGreedyPlayer` (`competition_rate=1.0`)

- **CLI updates (`models/cli.py`)**:
  - New flags:
    - `--output_path <DIR>`: where to write outputs (defaults to `results`).
    - `--test_player <CODE>`: label players of this type in reports.
    - `--rounds <N>`: repeat simulation with different seeds incremented from `--seed`.
    - `--detailed`: additionally write per-round JSON/TXT/CSV.
  - The `--player` flag accepts any known code from `main.py` (validation relaxed).
  - Returns a `Settings` dataclass with derived `total_players`.

- **Player codes (`main.py`)**:
  - Built-in: `pr` (Random), `pp` (Pause), `p_zipper` (Zipper)
  - Greedy: `p_balanced_greedy`, `p_selfless_greedy`, `p_selfish_greedy`
  - Bayesian tree search presets: `p_bst_low`, `p_bst_medium`, `p_bst_high`, `p_bst_dynamic`, `p_bst_dynamic_width`, `p_bst_dynamic_depth`

---

### Extended CLI Examples

- Run 10 rounds with per-round artifacts and a custom output directory:

```bash
uv run python main.py \
  --player p_balanced_greedy 4 \
  --player p_bst_low 2 \
  --length 200 --memory_size 500 --subjects 20 \
  --output_path results/exp1 \
  --test_player p_balanced_greedy \
  --rounds 10 --detailed
```

- Head-to-head between a greedy and a BST player (single round, CLI-only):

```bash
uv run python main.py --player p_balanced_greedy 1 --player p_bst_medium 1 --length 50
```

---

### Test Pipeline Script

A convenience script is provided at `shells/trivial_test_0911.sh` to reproduce common experiments.

1) Edit the variables at the top of the script:

- `test_player`: primary player to highlight
- `L` (length), `B` (memory_size), `S` (subjects)
- `gui_on`, `rounds`, `detailed_on`
- `player_list`: mix of other player codes for the complex environment

2) Make executable and run:

```bash
chmod +x shells/trivial_test_0911.sh
./shells/trivial_test_0911.sh
```

3) Outputs

- Results are saved under the derived `--output_path` inside `results/`.
- Example (as configured in the script):
  - `results/test_good_players_0913_p_balanced_greedy_L200B500S20/`
    - `complex_environment/results.csv` – per-type averages across rounds
    - If `--detailed`: `complex_environment/round_*/` with per-round JSON/TXT/CSV

---

### Notes

- The analysis CSVs use a consistent float precision and normalize metrics per turn where applicable.
- Player type names in outputs come from the concrete class names mapped in `main.py`.

