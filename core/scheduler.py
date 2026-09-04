from enum import Enum
import random
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .task import Task, TaskState
from .core import CPUCore


class StaticPolicy(Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    ARRIVAL_GREEDY = "arrival_greedy"  # Assign to core with lowest pending burst at arrival


class StaticScheduler:
    def __init__(self, num_cores: int = 4, policy: StaticPolicy = StaticPolicy.ROUND_ROBIN, seed: int = 42):
        if num_cores < 1:
            raise ValueError("Scheduler must have at least 1 core.")
        self.num_cores: int = num_cores
        self.policy: StaticPolicy = policy
        self.cores: List[CPUCore] = [CPUCore(core_id=i) for i in range(num_cores)]
        
        self.current_tick: int = 0
        self.completed_tasks: List[Task] = []
        self.all_tasks: List[Task] = []
        
        self._rr_index: int = 0
        self._rng = random.Random(seed)

    def _select_core(self, task: Task) -> CPUCore:
        """Determines core assignment based on the static distribution policy."""
        if self.policy == StaticPolicy.ROUND_ROBIN:
            chosen = self.cores[self._rr_index % self.num_cores]
            self._rr_index += 1
            return chosen
        elif self.policy == StaticPolicy.RANDOM:
            return self._rng.choice(self.cores)
        elif self.policy == StaticPolicy.ARRIVAL_GREEDY:
            # Pick core with minimum total pending burst (or shortest queue if tied)
            return min(self.cores, key=lambda c: (c.total_pending_burst, c.queue_length, c.core_id))
        else:
            return self.cores[0]

    def run(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Executes discrete-event multi-core scheduling simulation.
        Tasks are cloned so original definitions remain unmodified.
        """
        # Reset state
        self.current_tick = 0
        self.completed_tasks = []
        self._rr_index = 0
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
                    target_core = self._select_core(arriving_task)
                    target_core.assign_task(arriving_task)

            # 2. Step each core forward by 1 clock tick
            for core in self.cores:
                finished_task = core.step(self.current_tick)
                if finished_task is not None:
                    self.completed_tasks.append(finished_task)

            self.current_tick += 1

        makespan = self.current_tick
        return {
            "num_cores": self.num_cores,
            "policy": self.policy.value,
            "makespan": makespan,
            "completed_tasks": self.completed_tasks,
            "cores": self.cores,
        }
