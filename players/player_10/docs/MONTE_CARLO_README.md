# Monte Carlo Simulation Framework for Player10

This directory contains a comprehensive Monte Carlo simulation framework for testing and optimizing Player10 strategies without GUI.

## Overview

The framework allows you to:
- Run hundreds of simulations with different parameter configurations
- Test altruism probabilities, tau margins, and epsilon parameters
- Analyze results with statistical summaries and visualizations
- Find optimal parameter combinations through systematic testing

## Files

- `monte_carlo.py` - Core simulation framework
- `run_simulations.py` - Batch runner with predefined test scenarios
- `analyze_results.py` - Results analysis and visualization tools
- `example_usage.py` - Example scripts showing how to use the framework

## Quick Start

### 1. Run a Quick Test
```bash
cd players/player_10
python run_simulations.py --test quick --simulations 10
```

### 2. Compare Altruism Probabilities
```bash
python run_simulations.py --test altruism --simulations 100
```

### 3. Test Tau Sensitivity
```bash
python run_simulations.py --test tau --simulations 50
```

### 4. Analyze Results
```bash
python analyze_results.py simulation_results/altruism_comparison_1234567890.json --analysis
```

## Detailed Usage

### Running Simulations

#### Basic Usage
```python
from monte_carlo import MonteCarloSimulator

# Create simulator
simulator = MonteCarloSimulator("my_results")

# Run parameter sweep
results = simulator.run_parameter_sweep(
    altruism_probs=[0.0, 0.2, 0.5, 1.0],
    num_simulations=100,
        base_players={'p10': 10}
)

# Analyze results
analysis = simulator.analyze_results()
print(f"Best configuration: {analysis['best_configurations'][0]}")

# Save results
simulator.save_results("my_analysis.json")
```

#### Custom Configuration
```python
from monte_carlo import SimulationConfig

# Create custom configuration
config = SimulationConfig(
    altruism_prob=0.3,
    tau_margin=0.07,
    epsilon_fresh=0.03,
    epsilon_mono=0.08,
    seed=12345,
    players={'p10': 1, 'p0': 2, 'p1': 1}
)

# Run single simulation
result = simulator.run_single_simulation(config)
print(f"Total Score: {result.total_score}")
```

### Analyzing Results

#### Statistical Analysis
```python
from analyze_results import ResultsAnalyzer

# Load results
analyzer = ResultsAnalyzer("my_analysis.json")

# Print detailed analysis
analyzer.print_detailed_analysis()

# Create visualizations
analyzer.plot_altruism_comparison("altruism_plot.png")
analyzer.plot_score_distributions("distributions.png")
```

#### DataFrame Analysis
```python
# Convert to pandas DataFrame
df = analyzer.create_dataframe()

# Group by altruism probability
altruism_stats = df.groupby('altruism_prob')['total_score'].agg(['mean', 'std', 'count'])
print(altruism_stats)

# Find best configuration
best_config = df.loc[df['total_score'].idxmax()]
print(f"Best config: {best_config[['altruism_prob', 'tau_margin', 'total_score']]}")
```

## Test Scenarios

### 1. Altruism Comparison (`--test altruism`)
Tests different altruism probabilities: [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

**Use case:** Find the optimal altruism probability for your use case.

### 2. Tau Sensitivity (`--test tau`)
Tests different tau margin values: [0.01, 0.03, 0.05, 0.07, 0.10, 0.15]

**Use case:** Understand how sensitive the altruism gate is to the tau parameter.

### 3. Epsilon Sensitivity (`--test epsilon`)
Tests different epsilon values for freshness and monotony adjustments.

**Use case:** Fine-tune the context-aware threshold adjustments.

### 4. Quick Test (`--test quick`)
Runs a minimal test with 4 configurations and 10 simulations each.

**Use case:** Verify the framework is working correctly.

## Output Files

### Simulation Results
- **Format:** JSON
- **Location:** `simulation_results/` directory
- **Content:** All simulation data including configurations, scores, and metrics

### Analysis Plots
- **Format:** PNG (high resolution)
- **Content:** Statistical visualizations and comparisons
- **Types:** Line plots, heatmaps, distribution plots

## Metrics Tracked

### Performance Metrics
- **Total Score:** Overall conversation quality
- **Player10 Score:** Individual player performance
- **Conversation Length:** How long conversations last
- **Early Termination Rate:** How often conversations end early

### Strategy Metrics
- **Pause Count:** Number of pauses in conversation
- **Unique Items Used:** Diversity of items proposed
- **Execution Time:** Computational performance

## Configuration Parameters

### Altruism Parameters
- `ALTRUISM_USE_PROB`: Probability of using altruism strategy (0.0-1.0)
- `TAU_MARGIN`: Base altruism threshold
- `EPSILON_FRESH`: Freshness adjustment factor
- `EPSILON_MONO`: Monotony adjustment factor

### Simulation Parameters
- `num_simulations`: Number of runs per configuration
- `base_players`: Player composition for testing
- `subjects`: Number of conversation subjects
- `conversation_length`: Maximum conversation length

## Example Results

### Typical Output
```
=== SIMULATION RESULTS ===
Total simulations: 700
Unique configurations: 7

=== TOP 5 CONFIGURATIONS ===
1. Altruism: 0.3, Tau: 0.05, Fresh: 0.05, Mono: 0.05 -> Score: 15.42
2. Altruism: 0.2, Tau: 0.05, Fresh: 0.05, Mono: 0.05 -> Score: 15.38
3. Altruism: 0.5, Tau: 0.05, Fresh: 0.05, Mono: 0.05 -> Score: 15.21
4. Altruism: 0.1, Tau: 0.05, Fresh: 0.05, Mono: 0.05 -> Score: 15.18
5. Altruism: 0.7, Tau: 0.05, Fresh: 0.05, Mono: 0.05 -> Score: 15.05
```

## Dependencies

### Required
- `pandas` - Data analysis
- `numpy` - Numerical computations
- `matplotlib` - Basic plotting
- `seaborn` - Statistical visualizations

### Installation
```bash
pip install pandas numpy matplotlib seaborn
```

## Performance Tips

### For Large Simulations
1. **Use fewer simulations per config** for initial exploration
2. **Run in parallel** by splitting configurations across multiple processes
3. **Save intermediate results** to avoid losing progress
4. **Use smaller player counts** for faster execution

### For Analysis
1. **Load results into pandas** for custom analysis
2. **Use statistical tests** to validate significance
3. **Create multiple plot types** to understand different aspects
4. **Export data** for external analysis tools

## Troubleshooting

### Common Issues
1. **Import errors:** Make sure you're running from the project root
2. **Memory issues:** Reduce `num_simulations` or use fewer configurations
3. **Plot errors:** Install required visualization dependencies
4. **Slow execution:** Use smaller player counts or fewer simulations

### Getting Help
- Check the example scripts in `example_usage.py`
- Run with `--help` for command-line options
- Use the quick test to verify everything works

## Future Enhancements

- **Parallel execution** for faster simulations
- **More sophisticated analysis** with statistical tests
- **Real-time monitoring** of simulation progress
- **Integration with external optimization libraries**
- **Automated parameter tuning** using optimization algorithms
