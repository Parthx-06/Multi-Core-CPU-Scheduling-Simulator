# Implementation Plan - Phase 1: Baseline Multi-Core CPU Scheduler (Static Task Distribution)

## Overview
This plan establishes **Phase 1** of the *Load-Balanced CPU Scheduling for Multi-Core Systems* project. In this phase, we design and implement an event-driven multi-core CPU scheduling simulator with **static task distribution**, support for **balanced and skewed/uneven workloads**, and comprehensive evaluation of **load imbalance, speedup, efficiency, throughput, response time, and CPU utilization**. The architecture will be strictly modular to allow seamless integration of **Phase 2** (predictive AI/heuristic dynamic load migration).

---

## Architecture & Design

### 1. Core Simulation Engine (`core/`)
- **`Task` (`core/task.py`)**:
  - Properties: `task_id`, `arrival_time`, `burst_time`, `remaining_time`, `start_time`, `completion_time`, `assigned_core_id`.
  - Derived metrics: `waiting_time`, `response_time`, `turnaround_time`.
- **`CPUCore` (`core/core.py`)**:
  - Maintains a local queue of assigned tasks.
  - Per-tick execution: executes the active task using per-core policy (e.g., FCFS or Round-Robin time slice).
  - Tracks timeline of state (`BUSY`, `IDLE`), instantaneous queue length, and cumulative busy cycles.
- **`StaticScheduler` (`core/scheduler.py`)**:
  - Multi-core coordinator managing $M$ cores (default 4 cores, configurable 2, 4, 8, etc.).
  - Static distribution policies:
    1. `Round-Robin Static`: Assign task $i$ to core $i \pmod M$.
    2. `Random Static`: Uniformly random core selection.
    3. `Arrival-Time Greedy (Min-Load at arrival)`: Assign to the core with the smallest pending work at arrival, but **strictly no migration** after assignment.
  - Tracks discrete simulation clock (ticks).
- **`MetricsEngine` (`core/metrics.py`)**:
  - **Load Imbalance**: Standard deviation of core busy times, Jain's Fairness Index, and Peak-to-Average Load Ratio ($L_{max} / L_{avg}$).
  - **Makespan**: Total completion time across all cores.
  - **Speedup**: $\text{Makespan}_{1\text{-core}} / \text{Makespan}_{M\text{-cores}}$.
  - **Efficiency**: $\text{Speedup} / M$.
  - **Throughput**: Total tasks completed / total makespan.
  - **Response Time & Turnaround Time**: Mean, min, max, std-dev, and 95th percentile.
  - **CPU Utilization**: Per-core and system-wide average percentage.

### 2. Workload Generator (`core/workload.py`)
- **Balanced Workload**: Evenly distributed task arrivals and homogeneous burst times (e.g. Gaussian or uniform around a mean $\mu$).
- **Skewed / Uneven Workload**:
  - **Core Hotspot Skew**: Clustered burst times targeting subsets of assignments.
  - **Bimodal / Heavy-Tailed Skew**: Mixture of 80% lightweight tasks and 20% heavy elephant tasks.
  - **Burst Spike / Phase Skew**: Periodic bursts of high-burst tasks arriving at intervals.
- Save & Load presets (JSON/CSV) for reproducible benchmarks between Phase 1 and Phase 2.

### 3. Interactive CLI & Visualizer (`visualizer/` & `run_phase1.py`)
- **CLI Runner (`run_phase1.py`)**:
  - Run benchmark comparing Balanced vs. Skewed workloads on 2, 4, and 8 cores across static policies.
  - Formatted Rich tables displaying core-by-core utilization, queue sizes, response times, and load imbalance metrics.
- **Interactive Visual Report / Web Dashboard (`visualizer/dashboard.html` / `dashboard_server.py`)**:
  - Visual core execution Gantt timeline.
  - Core load & utilization comparison bar charts.
  - Queue length over time line graphs.
  - Export metrics to JSON for Phase 2 comparison.

---

## Proposed Changes

### Project Structure
```
OS_2/
├── core/
│   ├── __init__.py
│   ├── task.py             # Task data model & lifecycle
│   ├── core.py             # CPU Core simulation model
│   ├── scheduler.py        # Multi-core Static Scheduler
│   ├── workload.py         # Workload generator (balanced, skewed, bimodal)
│   └── metrics.py          # Metric calculations & statistical reporting
├── experiments/
│   ├── benchmark_runner.py # Automated runner comparing policies & workloads
│   └── presets/            # Saved benchmark workloads (JSON)
├── tests/
│   ├── test_scheduler.py   # Unit tests for core simulation logic
│   └── test_metrics.py     # Unit tests for metrics correctness
├── web/
│   ├── index.html          # Interactive visual dashboard
│   ├── style.css           # Premium styling & dark mode UI
│   └── app.js              # Timeline Gantt chart & metrics visualizer
├── run_phase1.py           # Main CLI driver script
└── README.md               # Documentation & usage instructions
```

---

## Verification Plan

### Automated Tests
- Run `pytest tests/` to verify:
  - Correct task state transitions and time metrics (Waiting, Response, Turnaround).
  - Core execution invariants: no negative burst, correct busy cycles.
  - Static distribution invariants: tasks stay on assigned core (no migration).
  - Metrics math: Jain's Fairness Index, speedup, makespan, load imbalance.

### Benchmark & Experiment Verification
- Run `python run_phase1.py` with:
  1. `balanced` workload on 4 cores.
  2. `skewed` workload on 4 cores.
- Confirm load imbalance is noticeably higher on skewed workloads with static round-robin, proving the baseline limitation that Phase 2 will solve.
- Inspect the generated visual dashboard / JSON reports.
