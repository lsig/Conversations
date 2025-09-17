"""
Comprehensive experiment runner for Player10 Monte Carlo simulations.

Defaults (tunable via CLI):
- Conversation lengths: 50, 100
- Altruism probabilities: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
- Tau margins: [-0.1, 0.0, 0.1, 0.5]
- Epsilon fresh: [0.05]
- Epsilon mono: [0.05]
- Player configuration: {'p10': 7}
- Simulations per configuration: 5

This uses the flexible framework to construct multiple TestConfiguration
instances (one per conversation length) and executes them in sequence.
"""

import argparse
from typing import List

from ..test_framework import (
    TestBuilder,
    FlexibleTestRunner,
    TestConfiguration,
)


def _frange(start: float, stop: float, step: float) -> List[float]:
    """Generate a list of floats from start to stop inclusive with a step."""
    values: List[float] = []
    x = start
    # Add a small epsilon to handle floating point boundaries
    eps = step / 10.0
    while x <= stop + eps:
        # Round to 10 decimals to avoid artifacts like 0.6000000000001
        values.append(round(x, 10))
        x += step
    # Clamp endpoints into [start, stop]
    values = [max(min(v, stop), start) for v in values]
    # Deduplicate while preserving order
    dedup: List[float] = []
    for v in values:
        if not dedup or abs(dedup[-1] - v) > 1e-9:
            dedup.append(v)
    return dedup


def build_configs(
    conv_lengths: List[int],
    altruism_values: List[float],
    tau_values: List[float],
    eps_fresh_values: List[float],
    eps_mono_values: List[float],
    p10_count: int,
    sims_per_config: int,
    output_dir: str,
) -> List[TestConfiguration]:
    configs: List[TestConfiguration] = []
    for length in conv_lengths:
        builder = TestBuilder(
            name=f"comprehensive_len{length}_p10_{p10_count}",
            description=(
                "Comprehensive sweep: altruism, tau, epsilons; "
                f"conversation_length={length}, p10={p10_count}"
            ),
        )
        config = (
            builder
            .altruism_range(altruism_values)
            .tau_range(tau_values)
            .epsilon_fresh_range(eps_fresh_values)
            .epsilon_mono_range(eps_mono_values)
            .player_configs([{ 'p10': p10_count }])
            .simulations(sims_per_config)
            .conversation_length(length)
            .output_dir(output_dir)
            .build()
        )
        configs.append(config)
    return configs


def main():
    parser = argparse.ArgumentParser(
        description="Run a comprehensive Player10 Monte Carlo experiment",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--sims", type=int, default=5, help="Simulations per configuration")
    parser.add_argument("--p10", type=int, default=7, help="Number of Player10 agents")
    parser.add_argument(
        "--conv-lengths", nargs="+", type=int, default=[50, 100],
        help="Conversation lengths to test"
    )
    parser.add_argument(
        "--altruism", nargs=3, type=float, metavar=("START", "STOP", "STEP"),
        default=[0.0, 1.0, 0.2], help="Altruism sweep as START STOP STEP"
    )
    parser.add_argument(
        "--tau", nargs="+", type=float, default=[-0.1, 0.0, 0.1, 0.5],
        help="Tau margin values to test"
    )
    parser.add_argument(
        "--eps-fresh", nargs="+", type=float, default=[0.05],
        help="Epsilon fresh values to test"
    )
    parser.add_argument(
        "--eps-mono", nargs="+", type=float, default=[0.05],
        help="Epsilon mono values to test"
    )
    parser.add_argument(
        "--output-dir", default="simulation_results",
        help="Directory to store results JSON files"
    )
    args = parser.parse_args()

    altruism_values = _frange(args.altruism[0], args.altruism[1], args.altruism[2])
    configs = build_configs(
        conv_lengths=args.conv_lengths,
        altruism_values=altruism_values,
        tau_values=args.tau,
        eps_fresh_values=args.eps_fresh,
        eps_mono_values=args.eps_mono,
        p10_count=args.p10,
        sims_per_config=args.sims,
        output_dir=args.output_dir,
    )

    runner = FlexibleTestRunner(args.output_dir)
    results_by_test = runner.run_multiple_tests(configs)

    total = sum(len(v) for v in results_by_test.values())
    print(f"\n=== COMPREHENSIVE EXPERIMENT COMPLETE ===")
    print(f"Total simulations across all configs: {total}")
    print(f"Test groups: {', '.join(results_by_test.keys())}")


if __name__ == "__main__":
    main()


