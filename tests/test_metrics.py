import pytest
from core.task import Task
from core.scheduler import StaticScheduler, StaticPolicy
from core.metrics import MetricsEngine


def test_metrics_calculation_balanced():
    # 4 tasks of burst 10 arriving at 0 on 4 cores
    scheduler = StaticScheduler(num_cores=4, policy=StaticPolicy.ROUND_ROBIN)
    tasks = [Task(task_id=i, arrival_time=0, burst_time=10) for i in range(4)]
    
    # Baseline 1-core run
    s1 = StaticScheduler(num_cores=1, policy=StaticPolicy.ROUND_ROBIN)
    res1 = s1.run(tasks)
    single_core_makespan = res1["makespan"]
    assert single_core_makespan == 40

    res4 = scheduler.run(tasks)
    metrics = MetricsEngine.calculate_metrics(res4, single_core_makespan=single_core_makespan)

    assert metrics["makespan"] == 10
    assert metrics["speedup"] == 4.0
    assert metrics["efficiency_pct"] == 100.0
    # Perfect balance: std dev of busy ticks = 0, Jain's index = 1.0
    assert metrics["load_imbalance"]["std_dev_busy_ticks"] == 0.0
    assert metrics["load_imbalance"]["jains_fairness_index"] == 1.0
    assert metrics["load_imbalance"]["peak_to_avg_ratio"] == 1.0


def test_metrics_skewed_imbalance_detection():
    scheduler = StaticScheduler(num_cores=2, policy=StaticPolicy.ROUND_ROBIN)
    # Task 0 -> Core 0 (burst 40), Task 1 -> Core 1 (burst 10)
    tasks = [
        Task(task_id=0, arrival_time=0, burst_time=40),
        Task(task_id=1, arrival_time=0, burst_time=10),
    ]
    res = scheduler.run(tasks)
    metrics = MetricsEngine.calculate_metrics(res, single_core_makespan=50)

    # Core 0 busy 40, Core 1 busy 10. Avg = 25. Makespan = 40.
    assert metrics["makespan"] == 40
    assert metrics["load_imbalance"]["std_dev_busy_ticks"] == 15.0
    # Jain's index must be strictly < 1.0
    assert metrics["load_imbalance"]["jains_fairness_index"] < 1.0
    assert metrics["load_imbalance"]["peak_to_avg_ratio"] == 1.6
    assert metrics["cpu_utilization"]["per_core_pct"][0] == 100.0
    assert metrics["cpu_utilization"]["per_core_pct"][1] == 25.0
