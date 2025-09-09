# Project 1

This is my fork. v2

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

