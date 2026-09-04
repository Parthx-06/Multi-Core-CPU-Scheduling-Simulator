import pytest
from core.task import Task
from core.core import CPUCore
from core.scheduler import StaticScheduler, StaticPolicy
from core.predictor import CoreLoadPredictor
from core.dynamic_scheduler import DynamicScheduler
from core.metrics import MetricsEngine
from core.workload import WorkloadGenerator


def test_predictor_forecasts_and_detects_imbalance():
    cores = [CPUCore(0), CPUCore(1)]
    predictor = CoreLoadPredictor(window_size=5)

    # Core 0 gets 3 heavy tasks, Core 1 gets 0 tasks
    for i in range(3):
        cores[0].assign_task(Task(task_id=i, arrival_time=0, burst_time=30))
    
    # Tick simulation for 3 ticks
    for t in range(3):
        cores[0].step(t)
        cores[1].step(t)
        predictor.update(t, cores)

    # Predictor should forecast higher load for Core 0
    p0 = predictor.predict_future_load(cores[0], horizon=10)
    p1 = predictor.predict_future_load(cores[1], horizon=10)
    assert p0 > p1
    assert p1 == 0.0

    # Imbalance detection should trigger
    should_migrate, donor, recipient, disp = predictor.detect_imbalance(cores, threshold=15.0)
    assert should_migrate is True
    assert donor == cores[0]
    assert recipient == cores[1]


def test_dynamic_scheduler_reduces_skewed_makespan():
    # Generate skewed hotspot workload
    tasks = WorkloadGenerator.generate_skewed_hotspot_workload(
        num_tasks=40, normal_burst=5, hotspot_burst=30, target_core_index=0, num_cores=4, seed=42
    )

    # Static Round-Robin Baseline
    static_scheduler = StaticScheduler(num_cores=4, policy=StaticPolicy.ROUND_ROBIN)
    static_res = static_scheduler.run(tasks)

    # Dynamic Predictive Scheduler
    dyn_scheduler = DynamicScheduler(
        num_cores=4,
        initial_policy=StaticPolicy.ROUND_ROBIN,
        imbalance_threshold=15.0,
        prediction_horizon=10,
        check_interval=2,
        migration_penalty=1
    )
    dyn_res = dyn_scheduler.run(tasks)

    # Invariant: All tasks must complete
    assert len(dyn_res["completed_tasks"]) == len(tasks)
    completed_ids = sorted([t.task_id for t in dyn_res["completed_tasks"]])
    original_ids = sorted([t.task_id for t in tasks])
    assert completed_ids == original_ids

    # Dynamic rebalancing should migrate work and significantly reduce makespan
    assert dyn_res["total_migrations"] > 0
    assert dyn_res["makespan"] < static_res["makespan"]

    # Calculate metrics
    static_m = MetricsEngine.calculate_metrics(static_res, single_core_makespan=static_res["makespan"] * 2)
    dyn_m = MetricsEngine.calculate_metrics(dyn_res, single_core_makespan=static_res["makespan"] * 2)
    comparison = MetricsEngine.compare_static_vs_dynamic(static_m, dyn_m)

    assert comparison["makespan_reduction_pct"] > 30.0
    assert comparison["fairness_gain"] > 0.3
