import pytest
from core.task import Task, TaskState
from core.core import CPUCore
from core.scheduler import StaticScheduler, StaticPolicy
from core.workload import WorkloadGenerator


def test_task_lifecycle():
    task = Task(task_id=1, arrival_time=5, burst_time=10)
    assert task.remaining_time == 10
    assert task.state == TaskState.PENDING
    assert task.waiting_time is None
    assert task.response_time is None

    # Simulate start and completion
    task.start_time = 8
    task.completion_time = 18
    assert task.response_time == 3
    assert task.turnaround_time == 13
    assert task.waiting_time == 3


def test_core_step_and_queue():
    core = CPUCore(core_id=0)
    task1 = Task(task_id=1, arrival_time=0, burst_time=2)
    task2 = Task(task_id=2, arrival_time=0, burst_time=3)

    core.assign_task(task1)
    core.assign_task(task2)
    assert core.queue_length == 2
    assert core.total_pending_burst == 5

    # Tick 0: task1 starts running
    done = core.step(0)
    assert done is None
    assert core.total_busy_ticks == 1
    assert task1.start_time == 0

    # Tick 1: task1 completes
    done = core.step(1)
    assert done == task1
    assert done.state == TaskState.COMPLETED
    assert done.completion_time == 2

    # Tick 2: task2 starts running
    done = core.step(2)
    assert done is None
    assert task2.start_time == 2


def test_round_robin_static_distribution():
    scheduler = StaticScheduler(num_cores=4, policy=StaticPolicy.ROUND_ROBIN)
    tasks = [Task(task_id=i, arrival_time=0, burst_time=5) for i in range(8)]
    result = scheduler.run(tasks)

    # 8 tasks across 4 cores = 2 tasks per core
    for core in scheduler.cores:
        core_tasks = [t for t in result["completed_tasks"] if t.assigned_core_id == core.core_id]
        assert len(core_tasks) == 2

    # Total work = 40 cycles. On 4 cores, makespan should be 10 ticks
    assert result["makespan"] == 10


def test_workload_generator_and_serialization(tmp_path):
    tasks = WorkloadGenerator.generate_balanced_workload(num_tasks=20, mean_burst=10, seed=123)
    assert len(tasks) == 20
    
    file_path = str(tmp_path / "test_workload.json")
    WorkloadGenerator.save_workload_to_json(tasks, file_path)
    loaded = WorkloadGenerator.load_workload_from_json(file_path)
    assert len(loaded) == 20
    assert loaded[0].task_id == tasks[0].task_id
    assert loaded[0].burst_time == tasks[0].burst_time
