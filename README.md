# Conversation Simulator

A multi-agent conversation simulation where players contribute items from their memory banks to create coherent, high-quality discussions. Players balance individual preferences with shared conversation goals to optimize collective and personal scores.

## Features

- **Multi-Agent Simulation**: Support for various player types with different strategies
- **Advanced AI Players**: Bayesian Tree Search players with configurable search depths and competition rates
- **Comprehensive Analysis**: Built-in tools for per-player and per-type performance analysis
- **Flexible Configuration**: Extensive CLI options for custom experiments
- **Visualization**: GUI mode for real-time conversation visualization
- **Batch Testing**: Automated test pipelines with statistical analysis

## Project Structure

```
conversations/
├── core/                    # Core simulation engine
│   ├── engine.py           # Main simulation logic
│   └── utils.py            # Analysis utilities and data structures
├── models/                 # Data models and CLI parsing
│   ├── cli.py             # Command-line argument parsing
│   ├── item.py            # Item representation
│   └── player.py          # Base player class
├── players/                # Player implementations
│   ├── bayesian_tree_search_player/  # Advanced BST players
│   ├── pause_player.py     # Pause-only player
│   ├── random_player.py    # Random selection player
│   ├── zipper_player/      # Zipper algorithm player
│   └── player_3/           # Custom player implementation
├── ui/                     # User interface components
├── results/                # Experiment outputs and analysis
├── shells/                 # Test automation scripts
└── main.py                 # Entry point
```

## Setup

### Prerequisites

- Python 3.13+
- uv (modern Python package manager)

### Installation

1. **Install uv**:
   ```bash
   # macOS with Homebrew
   brew install uv

   # Or follow: https://docs.astral.sh/uv/getting-started/installation/
   ```

2. **Install dependencies**:
   ```bash
   cd /path/to/conversations
   uv sync
   ```

### Dependencies

- `pygame>=2.6.1` - GUI visualization
- `openai` - AI model integration (optional)
- `ruff>=0.12.8` - Code formatting and linting

---

### CLI Arguments

The simulation can be configured using a variety of command-line arguments. If no arguments are provided, the simulation will run with a default set of parameters.

#### Core Options

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--gui` | `False` | Launches the graphical user interface to visualize the simulation |
| `--subjects` | `20` | Number of unique subjects in the simulation |
| `--memory_size` | `10` | Number of items each player has in their memory bank |
| `--length` | `10` | Maximum number of turns for the conversation |
| `--seed` | `91` | Random number generator seed for reproducibility |

#### Output Options

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--output_path` | `results` | Directory for saving simulation outputs |
| `--test_player` | `None` | Player type code to highlight in analysis reports |
| `--detailed` | `False` | Save per-round JSON/TXT/CSV files in addition to summary |

#### Experiment Options

| Argument | Default | Description |
| :--- | :--- | :--- |
| `--rounds` | `1` | Number of simulation rounds with different seeds |

#### Player Configuration

The `--player` argument allows you to specify the number of players of a certain type to include in the simulation. You can use this argument multiple times to create a mix of different players.

- **Format:** `--player <TYPE> <COUNT>`
- **`<TYPE>`:** A short code representing the player type.
- **`<COUNT>`:** The number of players of that type to add.

##### Available Player Types

| Code | Player Type | Description |
| :--- | :--- | :--- |
| `pr` | RandomPlayer | Random item selection |
| `pp` | PausePlayer | Only contributes pauses |
| `p3` | Player3 | Custom player implementation |
| `p_zipper` | ZipperPlayer | Zipper algorithm strategy |
| `p_balanced_greedy` | BalancedGreedyPlayer | Greedy with balanced competition (rate=0.5) |
| `p_selfless_greedy` | SelflessGreedyPlayer | Greedy prioritizing shared goals (rate=0.0) |
| `p_selfish_greedy` | SelfishGreedyPlayer | Greedy prioritizing individual goals (rate=1.0) |
| `p_bst_low` | BayesTreeBeamLow | BST search: depth=2, breadth=4 |
| `p_bst_medium` | BayesTreeBeamMedium | BST search: depth=3, breadth=16 |
| `p_bst_high` | BayesTreeBeamHigh | BST search: depth=6, breadth=128 |
| `p_bst_dynamic` | BayesTreeDynamicStandard | BST with dynamic breadth (0.5 × memory size) |
| `p_bst_dynamic_width` | BayesTreeDynamicWidth | BST with dynamic breadth (4 × memory size) |
| `p_bst_dynamic_depth` | BayesTreeDynamicDepth | BST with depth=6, dynamic breadth |

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

## Usage Examples

### Basic Usage

Run a simple simulation with random players:
```bash
uv run main.py --player pr 5 --length 20
```

### GUI Mode

Launch with visualization:
```bash
uv run main.py --gui --player p_balanced_greedy 3 --player pr 2 --length 30
```

### Advanced Players

Test Bayesian Tree Search players:
```bash
uv run main.py --player p_bst_medium 2 --player p_selfless_greedy 2 --length 50
```

### Batch Experiments

Run multiple rounds with analysis:
```bash
uv run main.py \
  --player p_bst_low 4 \
  --player p_balanced_greedy 4 \
  --length 100 \
  --memory_size 20 \
  --rounds 5 \
  --detailed \
  --output_path results/experiment1
```

### Head-to-Head Comparison

Compare different strategies:
```bash
uv run main.py --player p_bst_medium 1 --player p_selfish_greedy 1 --length 40
```

## Scoring System

### Shared Goals (affect all players)
- **Importance**: Sum of item importance values
- **Coherence**: ±1 based on subject overlap with context window
- **Freshness**: Bonus for introducing novel subjects after pauses
- **Non-monotonousness**: Penalty for repetitive subject sequences
- **Non-repetition**: Repeated items get zero score

### Individual Goals
- **Preference Bonus**: Based on player's ranked subject preferences
- Items with preferred subjects get higher individual scores

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

### Output Files
- `results.csv`: Per-type performance summary across rounds
- `simulation_results.json`: Complete conversation data
- `analysis.txt`: Human-readable performance report
- `player_metrics.csv`: Per-player detailed metrics

---

## Test Automation

Use provided shell scripts for systematic testing:

```bash
uv run python main.py \
  --player p_balanced_greedy 4 \
  --player p_bst_low 2 \
  --length 200 --memory_size 500 --subjects 20 \
  --output_path results/exp1 \
  --test_player p_balanced_greedy \
  --rounds 10 --detailed
```

Configure test parameters in the script:
- Player combinations
- Memory sizes and conversation lengths
- Number of rounds
- Output directories

## Development

### Code Quality

This project uses Ruff for code formatting and linting:

```bash
# Check formatting
uv run ruff format --check

# Auto-format code
uv run ruff format

# Check linting
uv run ruff check

# Auto-fix linting issues
uv run ruff check --fix
```

### Architecture Notes

- **Modular Design**: Player implementations are completely encapsulated
- **Configurable Competition**: `competition_rate` balances individual vs. shared goals
- **Beam Search**: BST players use probabilistic tree search with expectation maximization
- **Analysis Pipeline**: Built-in tools for systematic performance evaluation

## License

This project is developed for educational purposes as part of COMS 4444 coursework.

## Contributing

1. Follow the code quality guidelines using Ruff
2. Add new player types to `main.py`'s `g_player_classes` dictionary
3. Update this README when adding new features
4. Test new players with the provided shell scripts

