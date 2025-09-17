"""
Parallel execution utilities for Monte Carlo simulations.

This module centralizes multiprocessing concerns to keep the test framework clean.
"""

from __future__ import annotations

import os
import concurrent.futures
from typing import Iterable, Tuple

from .monte_carlo import MonteCarloSimulator, SimulationConfig, SimulationResult


def run_simulation_task(args: Tuple[SimulationConfig, str]) -> SimulationResult:
    """Run a single simulation in an isolated process.

    Creates a fresh MonteCarloSimulator for process safety; returns the result.
    """
    sim_config, output_dir = args
    local_sim = MonteCarloSimulator(output_dir)
    return local_sim.run_single_simulation(sim_config)


def execute_in_parallel(tasks: Iterable[Tuple[SimulationConfig, str]], workers: int | None = None) -> Iterable[SimulationResult]:
    """Execute simulation tasks in parallel and yield results as they complete.

    Args:
        tasks: iterable of (SimulationConfig, output_dir)
        workers: number of worker processes (default: os.cpu_count())
    """
    max_workers = workers or os.cpu_count() or 1
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        for result in executor.map(run_simulation_task, tasks):
            yield result


