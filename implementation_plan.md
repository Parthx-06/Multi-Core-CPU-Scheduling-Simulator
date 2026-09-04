# Implementation Plan - Phase 2: Dynamic Load Balancing with Predictive AI & Adaptive Task Migration

## Overview
In **Phase 1**, we established the baseline multi-core CPU scheduler and proved that **Static Task Distribution fails under skewed workloads** (efficiency collapsed to 37.3%, Jain's Fairness dropped to 0.516, and Core 0 became a bottleneck for 721 ticks while other cores sat idle for 600+ ticks).

In **Phase 2**, we design and implement **Dynamic Load-Balanced CPU Scheduling**:
1. **Load Predictor Engine**: Continuously tracks queue lengths, execution rates, and pending bursts using Exponential Moving Average (EMA) and linear trend forecasting to predict future core load before severe bottlenecks accumulate.
2. **Dynamic Migration / Work Stealing Controller**: Dynamically moves pending tasks from overloaded cores to underloaded/idle cores with configurable migration overhead penalties.
3. **Phase 1 vs. Phase 2 Direct Benchmark Suite & Web Visualizer**: Comprehensive comparative analysis proving drastic reductions in makespan, load imbalance, and response times.

---

## User Review Required

> [!IMPORTANT]
> **Migration Overhead Modeling**: In physical multi-core CPUs, migrating a task across cores incurs cache invalidation and context switch penalties. We will include a realistic `migration_penalty_ticks` (default: 1 tick, configurable: 0-5 ticks) to demonstrate that the predictive scheduler optimizes load without thrashing.

> [!NOTE]
> **Reproducibility**: All experiments will run against the exact same workload seeds and JSON presets generated in Phase 1 (`balanced.json`, `skewed_hotspot.json`, `skewed_bimodal.json`) to ensure scientifically rigorous side-by-side comparisons.

---

## Proposed Changes

### Core Engine (`core/`)

#### [NEW] [predictor.py](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/predictor.py)
- `CoreLoadPredictor`:
  - Maintains sliding history of queue lengths $Q_i(t)$, execution velocity $V_i(t)$, and remaining burst demand $W_i(t)$ for each core.
  - Predicts future load $\hat{L}_i(t + H)$ for horizon $H$:
    $$\hat{L}_i(t + H) = W_i(t) + \alpha \cdot Q_i(t) - \beta \cdot V_i(t) \cdot H$$
  - Detects impending imbalance when $\max_i(\hat{L}_i) - \min_j(\hat{L}_j) > \text{Threshold}$.
  - Supports two predictive models:
    1. **Adaptive EMA / Gradient Heuristic** (lightweight, zero overhead).
    2. **Linear Regression Trend Predictor** (windowed velocity forecasting).

#### [NEW] [dynamic_scheduler.py](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/dynamic_scheduler.py)
- `DynamicScheduler`:
  - Inherits/coordinates $M$ `CPUCore` instances.
  - Initial distribution (e.g. Round-Robin or Arrival Greedy) followed by active runtime dynamic balancing.
  - Imbalance checking interval (e.g., every $k=5$ ticks or when any core becomes idle).
  - Migration Controller:
    - Identifies donor core ($\max \hat{L}$) and recipient core ($\min \hat{L}$).
    - Migrates queued tasks (from tail of ready queue to preserve cache locality of head task).
    - Logs migration events: `{"tick": t, "task_id": tid, "from_core": c1, "to_core": c2, "cost": penalty}`.
    - Applies realistic context-switch/migration penalty ticks.

#### [MODIFY] [core.py](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/core.py)
- Add `migration_penalty_remaining` to handle migration latency when receiving a migrated task.
- Add `remove_task_for_migration()` to safely extract ready tasks for transfer.
- Add `migration_count` tracking.

#### [MODIFY] [metrics.py](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/metrics.py)
- Add tracking for total migrations, migration overhead cycles, and load balance improvement percentage relative to Phase 1.

---

### Benchmarking & Comparison Suite (`experiments/`)

#### [NEW] [run_phase2.py](file:///c:/Users/parth/OneDrive/Documents/OS_2/run_phase2.py)
- CLI benchmark runner executing both Phase 1 (Static) and Phase 2 (Dynamic Predictive) side-by-side.
- Formatted Rich comparison tables highlighting:
  - Makespan reduction ($\Delta \text{Makespan}\%$)
  - Speedup increase
  - Efficiency improvement
  - Jain's Fairness Index restoration ($\to 0.99$)
  - Latency (Avg & P95 response time) reduction
  - Total migrations performed.

---

### Interactive Web Dashboard (`web/`)

#### [MODIFY] [server.py](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/server.py)
- Support `scheduler_type: "dynamic_predictive"` or `"static"` in `/api/simulate`.
- Endpoint `/api/compare`: Runs both Static and Dynamic on the same workload and returns a side-by-side diff.

#### [MODIFY] [index.html](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/index.html)
- Add "Phase 2: Dynamic Predictive Migration" toggle.
- Add migration penalty slider and prediction horizon slider.
- Add "Phase 1 vs Phase 2 Side-by-Side Comparison" view.
- Add Migration Event markers to the Gantt chart.

#### [MODIFY] [app.js](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/app.js) & [style.css](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/style.css)
- Visual indicators for migrated tasks in the Gantt timeline.
- Dynamic prediction curve vs actual core load chart.

---

### In-Depth Guide & Documentation

#### [NEW] [PHASE2_GUIDE.md](file:///c:/Users/parth/OneDrive/Documents/OS_2/PHASE2_GUIDE.md)
- In-depth Hinglish + English guide explaining:
  - Mathematics of core load prediction (EMA, velocity, horizon).
  - Work stealing and task migration algorithms.
  - Trade-offs: Migration overhead vs imbalance recovery.
  - Full numerical comparison between Phase 1 and Phase 2.

---

## Verification Plan

### Automated Tests
- Unit tests in `tests/test_dynamic_scheduler.py`:
  - Verify task migration logic (task leaves donor core queue, arrives at recipient core).
  - Verify migration penalty accounting.
  - Verify predictor correctness on synthetic increasing/decreasing queues.
  - Verify no task loss or duplication during migration.
- Run `pytest tests/`.

### Benchmark & Performance Verification
- Run `python run_phase2.py`:
  - Under `skewed_hotspot` (4 cores):
    - Verify Makespan drops from **724 ticks** to **~260-280 ticks**.
    - Verify Speedup improves from **1.49x** to **~3.7x+**.
    - Verify Jain's Fairness Index improves from **0.516** to **>0.98**.
    - Verify P95 Response Time drops from **461 ticks** to **<100 ticks**.
- Verify Web dashboard at `http://127.0.0.1:5000` with migration markers in Gantt view.
