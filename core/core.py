from collections import deque
from typing import Optional, List, Dict, Any
from .task import Task, TaskState


class CPUCore:
    def __init__(self, core_id: int):
        self.core_id: int = core_id
        self.ready_queue: deque[Task] = deque()
        self.current_task: Optional[Task] = None
        
        self.total_busy_ticks: int = 0
        self.total_idle_ticks: int = 0
        
        # Migration tracking for Phase 2
        self.migrations_in: int = 0
        self.migrations_out: int = 0
        self.migration_overhead_ticks: int = 0
        self.migration_penalty_remaining: int = 0

        # Per-tick timeline log for Gantt charts and dynamics analysis
        # List of dicts: {"tick": int, "task_id": Optional[int], "state": str, "queue_len": int}
        self.timeline: List[Dict[str, Any]] = []

    def assign_task(self, task: Task) -> None:
        """Assigns a task to this core's local ready queue (Initial distribution)."""
        task.assigned_core_id = self.core_id
        task.state = TaskState.READY
        self.ready_queue.append(task)

    def extract_task_for_migration(self, max_migrations_per_task: int = 1) -> Optional[Task]:
        """
        Extracts a task eligible for migration from ready queue.
        Enforces anti-thrashing (max_migrations_per_task).
        """
        for i in reversed(range(len(self.ready_queue))):
            t = self.ready_queue[i]
            if t.migration_count < max_migrations_per_task:
                del self.ready_queue[i]
                t.migration_count += 1
                self.migrations_out += 1
                return t
        return None

    def receive_migrated_task(self, task: Task, penalty_ticks: int = 1) -> None:
        """Receives a task migrated from another core, applying migration penalty."""
        task.assigned_core_id = self.core_id
        
        # If core is idle, place task into running state immediately so it's not re-migrated
        if self.current_task is None:
            self.current_task = task
            task.state = TaskState.RUNNING
        else:
            task.state = TaskState.READY
            self.ready_queue.append(task)

        self.migrations_in += 1
        if penalty_ticks > 0:
            self.migration_penalty_remaining += penalty_ticks
            self.migration_overhead_ticks += penalty_ticks

    @property
    def queue_length(self) -> int:
        """Number of tasks waiting in the ready queue."""
        return len(self.ready_queue)

    @property
    def total_pending_burst(self) -> int:
        """Total execution cycles remaining across active task, queue, and migration overhead."""
        pending = sum(t.remaining_time for t in self.ready_queue)
        if self.current_task is not None:
            pending += self.current_task.remaining_time
        pending += self.migration_penalty_remaining
        return pending

    @property
    def utilization(self) -> float:
        """Fraction of time spent executing tasks."""
        total = self.total_busy_ticks + self.total_idle_ticks
        return (self.total_busy_ticks / total) if total > 0 else 0.0

    def step(self, current_tick: int) -> Optional[Task]:
        """
        Executes one clock tick on this core.
        Returns the completed Task if a task finishes in this tick, otherwise None.
        """
        # Handle migration context switch penalty if active
        if self.migration_penalty_remaining > 0:
            self.migration_penalty_remaining -= 1
            self.total_busy_ticks += 1
            self.timeline.append({
                "tick": current_tick,
                "task_id": None,
                "state": "MIGRATING",
                "queue_len": len(self.ready_queue)
            })
            return None

        # If core is idle, pick next task from ready queue
        if self.current_task is None and self.ready_queue:
            self.current_task = self.ready_queue.popleft()
            self.current_task.state = TaskState.RUNNING
            if self.current_task.start_time is None:
                self.current_task.start_time = current_tick

        completed_task: Optional[Task] = None

        if self.current_task is not None:
            # Core is BUSY executing current task
            executed_task_id = self.current_task.task_id
            self.current_task.remaining_time -= 1
            self.total_busy_ticks += 1
            
            self.timeline.append({
                "tick": current_tick,
                "task_id": executed_task_id,
                "state": "BUSY",
                "queue_len": len(self.ready_queue)
            })

            # Check if task completed
            if self.current_task.remaining_time <= 0:
                self.current_task.state = TaskState.COMPLETED
                self.current_task.completion_time = current_tick + 1
                completed_task = self.current_task
                self.current_task = None
        else:
            # Core is IDLE
            self.total_idle_ticks += 1
            self.timeline.append({
                "tick": current_tick,
                "task_id": None,
                "state": "IDLE",
                "queue_len": 0
            })

        return completed_task

    def reset(self) -> None:
        """Reset core state."""
        self.ready_queue.clear()
        self.current_task = None
        self.total_busy_ticks = 0
        self.total_idle_ticks = 0
        self.migrations_in = 0
        self.migrations_out = 0
        self.migration_overhead_ticks = 0
        self.migration_penalty_remaining = 0
        self.timeline.clear()
