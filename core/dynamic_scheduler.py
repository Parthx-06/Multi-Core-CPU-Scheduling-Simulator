from typing import List, Dict, Any, Optional
from collections import defaultdict

from .task import Task, TaskState
from .core import CPUCore
from .predictor import CoreLoadPredictor
from .scheduler import StaticPolicy


class DynamicScheduler:
    """
    Phase 2 Dynamic Load-Balanced CPU Scheduler:
    Combines initial task mapping with predictive runtime work-stealing/migration.
    Uses CoreLoadPredictor to forecast future loads and balance cores before severe latency builds up.
    """
    def __init__(
        self,
        num_cores: int = 4,
        initial_policy: StaticPolicy = StaticPolicy.ROUND_ROBIN,
        imbalance_threshold: float = 15.0,
        prediction_horizon: int = 10,
        check_interval: int = 3,
        migration_penalty: int = 1,
        seed: int = 42,
    ):
        if num_cores < 1:
            raise ValueError("Scheduler must have at least 1 core.")
        self.num_cores: int = num_cores
        self.initial_policy: StaticPolicy = initial_policy
        self.imbalance_threshold: float = imbalance_threshold
        self.prediction_horizon: int = prediction_horizon
        self.check_interval: int = check_interval
        self.migration_penalty: int = migration_penalty
        
        self.cores: List[CPUCore] = [CPUCore(core_id=i) for i in range(num_cores)]
        self.predictor: CoreLoadPredictor = CoreLoadPredictor()
        
        self.current_tick: int = 0
        self.completed_tasks: List[Task] = []
        self.all_tasks: List[Task] = []
        self.migrations: List[Dict[str, Any]] = []
        
        self._rr_index: int = 0

    def _select_initial_core(self, task: Task) -> CPUCore:
        """Initial task placement before dynamic rebalancing."""
        if self.initial_policy == StaticPolicy.ROUND_ROBIN:
            chosen = self.cores[self._rr_index % self.num_cores]
            self._rr_index += 1
            return chosen
        elif self.initial_policy == StaticPolicy.ARRIVAL_GREEDY:
            return min(self.cores, key=lambda c: (c.total_pending_burst, c.queue_length, c.core_id))
        else:
            return self.cores[0]

    def _attempt_migration(self) -> None:
        """Checks for predicted imbalance and performs dynamic task migration if warranted."""
        should_migrate, donor, recipient, disparity = self.predictor.detect_imbalance(
            self.cores,
            threshold=self.imbalance_threshold,
            horizon=self.prediction_horizon
        )

        if should_migrate and donor is not None and recipient is not None:
            # Transfer a task from donor's ready queue to recipient's queue
            migrated_task = donor.extract_task_for_migration()
            if migrated_task is not None:
                recipient.receive_migrated_task(migrated_task, penalty_ticks=self.migration_penalty)
                
                self.migrations.append({
                    "tick": self.current_tick,
                    "task_id": migrated_task.task_id,
                    "from_core": donor.core_id,
                    "to_core": recipient.core_id,
                    "burst_time": migrated_task.burst_time,
                    "predicted_disparity": round(disparity, 2),
                    "penalty_ticks": self.migration_penalty,
                })

    def run(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Executes discrete simulation with dynamic predictive load balancing.
        """
        # Reset state
        self.current_tick = 0
        self.completed_tasks = []
        self.migrations = []
        self._rr_index = 0
        self.predictor.reset()
        for core in self.cores:
            core.reset()

        # Clone input tasks
        self.all_tasks = [t.clone() for t in tasks]
        total_tasks_count = len(self.all_tasks)

        # Index pending tasks by arrival time
        arrival_map: Dict[int, List[Task]] = defaultdict(list)
        for task in self.all_tasks:
            arrival_map[task.arrival_time].append(task)

        # Main tick loop
        while len(self.completed_tasks) < total_tasks_count:
            # 1. Handle task arrivals at this tick
            if self.current_tick in arrival_map:
                for arriving_task in arrival_map[self.current_tick]:
                    target_core = self._select_initial_core(arriving_task)
                    target_core.assign_task(arriving_task)

            # 2. Update predictor rolling history
            self.predictor.update(self.current_tick, self.cores)

            # 3. Trigger dynamic migration check periodically or when any core has 0 work
            is_idle_core_present = any(c.current_task is None and c.queue_length == 0 for c in self.cores)
            if (self.current_tick % self.check_interval == 0) or is_idle_core_present:
                self._attempt_migration()

            # 4. Step each core forward by 1 clock tick
            for core in self.cores:
                finished_task = core.step(self.current_tick)
                if finished_task is not None:
                    self.completed_tasks.append(finished_task)

            self.current_tick += 1

        makespan = self.current_tick
        return {
            "num_cores": self.num_cores,
            "policy": f"dynamic_predictive_{self.initial_policy.value}",
            "makespan": makespan,
            "completed_tasks": self.completed_tasks,
            "cores": self.cores,
            "migrations": self.migrations,
            "total_migrations": len(self.migrations),
        }
