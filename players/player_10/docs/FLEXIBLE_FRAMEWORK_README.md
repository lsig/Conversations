# Flexible Test Framework for Player10

A powerful, flexible framework for running Monte Carlo simulations with custom test configurations. No more predefined test types - create exactly the tests you need!

## Key Features

- **🎯 Custom Test Configurations**: Define any combination of parameters and player setups
- **🔧 Builder Pattern**: Easy-to-use fluent API for creating tests
- **📊 Multiple Test Types**: Run single tests or batches of related tests
- **⚡ Efficient Execution**: Optimized for running many simulations quickly
- **📈 Default Conversation Length**: 50 turns (configurable)
- **💾 Flexible Output**: Save results, print progress, or run silently

## Quick Start

### Command Line Usage

```bash
# Run predefined altruism comparison
python -m players.player_10.flexible_runner --predefined altruism

# Run custom test with specific parameters
python -m players.player_10.flexible_runner --name "my_test" --altruism 0.0 0.5 1.0 --simulations 100

# Test against random players
python -m players.player_10.flexible_runner --name "random_test" --players '{"p10": 10, "pr": 5}' --altruism 0.0 0.5 1.0
```

### Python API Usage

```python
from players.player_10.test_framework import TestBuilder, FlexibleTestRunner

# Create custom test
config = (TestBuilder("my_test", "Test different altruism probabilities")
          .altruism_range([0.0, 0.2, 0.5, 1.0])
          .player_configs([{'p10': 10}])
          .simulations(50)
          .conversation_length(50)
          .build())

# Run test
runner = FlexibleTestRunner()
results = runner.run_test(config)
```

## Framework Components

### 1. TestBuilder
Fluent API for creating test configurations:

```python
config = (TestBuilder("test_name", "description")
          .altruism_range([0.0, 0.5, 1.0])           # Altruism probabilities
          .tau_range([0.03, 0.05, 0.07])             # Tau margins
          .epsilon_fresh_range([0.03, 0.05])         # Epsilon fresh values
          .epsilon_mono_range([0.03, 0.05])          # Epsilon mono values
          .player_configs([{'p10': 10}])             # Player configurations
          .simulations(50)                           # Simulations per config
          .conversation_length(50)                   # Conversation length
          .subjects(20)                              # Number of subjects
          .memory_size(10)                           # Memory size
          .output_dir("my_results")                  # Output directory
          .build())
```

### 2. FlexibleTestRunner
Executes test configurations:

```python
runner = FlexibleTestRunner("output_directory")

# Run single test
results = runner.run_test(config)

# Run multiple tests
all_results = runner.run_multiple_tests([config1, config2, config3])
```

### 3. Predefined Tests
Ready-to-use test configurations:

```python
from players.player_10.test_framework import (
    create_altruism_comparison_test,
    create_random_players_test,
    create_scalability_test,
    create_parameter_sweep_test,
    create_mixed_opponents_test
)

# Use predefined tests
config = create_altruism_comparison_test()
```

## Test Configuration Options

### Parameter Ranges
- **altruism_range**: List of altruism probabilities [0.0, 1.0]
- **tau_range**: List of tau margin values
- **epsilon_fresh_range**: List of epsilon fresh values
- **epsilon_mono_range**: List of epsilon mono values

### Player Configurations
- **Single player type**: `{'p10': 10}`
- **Multiple player types**: `{'p10': 10, 'pr': 5}`
- **Mixed opponents**: `{'p10': 10, 'p0': 2, 'p1': 2, 'p2': 2, 'pr': 4}`

### Simulation Parameters
- **simulations**: Number of simulations per configuration
- **conversation_length**: Length of conversations (default: 50)
- **subjects**: Number of conversation subjects (default: 20)
- **memory_size**: Player memory size (default: 10)

## Example Test Scenarios

### 1. Altruism Comparison
```python
config = (TestBuilder("altruism_comparison")
          .altruism_range([0.0, 0.2, 0.5, 1.0])
          .player_configs([{'p10': 10}])
          .simulations(100)
          .build())
```

### 2. Random Players Test
```python
config = (TestBuilder("random_players")
          .altruism_range([0.0, 0.5, 1.0])
          .player_configs([
              {'p10': 10, 'pr': 2},
              {'p10': 10, 'pr': 5},
              {'p10': 10, 'pr': 10}
          ])
          .simulations(50)
          .build())
```

### 3. Parameter Sweep
```python
config = (TestBuilder("parameter_sweep")
          .altruism_range([0.0, 0.5, 1.0])
          .tau_range([0.03, 0.05, 0.07])
          .epsilon_fresh_range([0.03, 0.05])
          .epsilon_mono_range([0.03, 0.05])
          .player_configs([{'p10': 10}])
          .simulations(25)
          .build())
```

### 4. Mixed Opponents
```python
config = (TestBuilder("mixed_opponents")
          .altruism_range([0.0, 0.5, 1.0])
          .player_configs([
              {'p10': 10, 'p0': 2, 'p1': 2, 'pr': 4},
              {'p10': 10, 'pr': 8},
              {'p10': 10}
          ])
          .simulations(50)
          .build())
```

## Command Line Interface

### Basic Usage
```bash
# Run predefined test
python -m players.player_10.flexible_runner --predefined altruism

# Run custom test
python -m players.player_10.flexible_runner --name "my_test" --altruism 0.0 0.5 1.0
```

### Advanced Usage
```bash
# Test against random players
python -m players.player_10.flexible_runner \
  --name "random_test" \
  --players '{"p10": 10, "pr": 5}' \
  --altruism 0.0 0.5 1.0 \
  --simulations 100

# Parameter sweep
python -m players.player_10.flexible_runner \
  --name "sweep" \
  --altruism 0.0 0.5 1.0 \
  --tau 0.03 0.05 0.07 \
  --epsilon-fresh 0.03 0.05 \
  --epsilon-mono 0.03 0.05 \
  --simulations 50

# Multiple player configurations
python -m players.player_10.flexible_runner \
  --name "multi_config" \
  --players '{"p10": 10}' '{"p10": 10, "pr": 2}' '{"p10": 10, "pr": 5}' \
  --altruism 0.0 0.5 1.0
```

### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--predefined` | Run predefined test | `--predefined altruism` |
| `--name` | Test name | `--name "my_test"` |
| `--description` | Test description | `--description "Test description"` |
| `--altruism` | Altruism probabilities | `--altruism 0.0 0.5 1.0` |
| `--tau` | Tau margins | `--tau 0.03 0.05 0.07` |
| `--epsilon-fresh` | Epsilon fresh values | `--epsilon-fresh 0.03 0.05` |
| `--epsilon-mono` | Epsilon mono values | `--epsilon-mono 0.03 0.05` |
| `--players` | Player configurations | `--players '{"p10": 10}' '{"p10": 10, "pr": 5}'` |
| `--simulations` | Simulations per config | `--simulations 100` |
| `--conversation-length` | Conversation length | `--conversation-length 50` |
| `--subjects` | Number of subjects | `--subjects 20` |
| `--memory-size` | Memory size | `--memory-size 10` |
| `--output-dir` | Output directory | `--output-dir "my_results"` |
| `--no-save` | Don't save results | `--no-save` |
| `--quiet` | Suppress progress | `--quiet` |

## Predefined Tests

| Test | Description | Parameters |
|------|-------------|------------|
| `altruism` | Altruism comparison | Altruism: [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0] |
| `random2` | vs 2 random players | Altruism: [0.0, 0.2, 0.5, 1.0] |
| `random5` | vs 5 random players | Altruism: [0.0, 0.2, 0.5, 1.0] |
| `random10` | vs 10 random players | Altruism: [0.0, 0.2, 0.5, 1.0] |
| `scalability` | Scalability test | Tests 2, 5, 10 random players |
| `parameter_sweep` | Comprehensive sweep | Multiple parameter ranges |
| `mixed` | Mixed opponents | Various opponent combinations |

## Output and Analysis

### Results Format
Results are saved as JSON files with:
- Configuration parameters
- Simulation results
- Performance metrics
- Execution statistics

### Analysis
Use the existing analysis tools:
```python
from players.player_10.analyze_results import ResultsAnalyzer

analyzer = ResultsAnalyzer("results.json")
analyzer.print_detailed_analysis()
analyzer.plot_altruism_comparison()
```

## Performance Tips

### For Large Tests
1. **Start small**: Use fewer simulations initially
2. **Use shorter conversations**: Reduce conversation_length for faster testing
3. **Focus parameters**: Test fewer parameter combinations initially
4. **Use quiet mode**: `--quiet` for batch processing

### For Quick Testing
1. **Use predefined tests**: They're optimized for common scenarios
2. **Reduce simulations**: Use 10-20 simulations for quick validation
3. **Shorter conversations**: Use 20-30 turn conversations
4. **Fewer parameters**: Test 2-3 parameter values initially

## Examples

See `flexible_examples.py` for comprehensive examples of:
- Basic altruism testing
- Random player comparisons
- Custom parameter sweeps
- Mixed opponent testing
- Conversation length impact studies
- Quick validation tests
- Comprehensive studies

## Migration from Old Framework

The old `run_simulations.py` is still available, but the new flexible framework is recommended:

### Old Way
```bash
python -m players.player_10.run_simulations --test altruism --simulations 100
```

### New Way
```bash
python -m players.player_10.flexible_runner --predefined altruism --simulations 100
```

Or for custom tests:
```python
config = TestBuilder("my_test").altruism_range([0.0, 0.5, 1.0]).build()
runner = FlexibleTestRunner()
results = runner.run_test(config)
```

The flexible framework provides much more control and customization options while maintaining the simplicity of the predefined tests.
