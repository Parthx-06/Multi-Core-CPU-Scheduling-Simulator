from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TaskState(Enum):
    PENDING = "PENDING"      # Not yet arrived
    READY = "READY"          # In core queue, waiting to execute
    RUNNING = "RUNNING"      # Currently executing on core
    COMPLETED = "COMPLETED"  # Finished execution


@dataclass
class Task:
    task_id: int
    arrival_time: int
    burst_time: int
    remaining_time: int = field(init=False)
    state: TaskState = field(default=TaskState.PENDING)
    
    assigned_core_id: Optional[int] = None
    start_time: Optional[int] = None
    completion_time: Optional[int] = None
    
    # Metadata for tracking / visualization
    tag: str = "normal"  # "normal", "heavy", "light"

    def __post_init__(self):
        self.remaining_time = self.burst_time

    @property
    def waiting_time(self) -> Optional[int]:
        """Total time spent waiting in queue after arrival until completion minus burst time."""
        if self.completion_time is not None:
            return self.turnaround_time - self.burst_time
        return None

    @property
    def response_time(self) -> Optional[int]:
        """Time from arrival to first execution start."""
        if self.start_time is not None:
            return self.start_time - self.arrival_time
        return None

    @property
    def turnaround_time(self) -> Optional[int]:
        """Total time from arrival to completion."""
        if self.completion_time is not None:
            return self.completion_time - self.arrival_time
        return None

    def clone(self) -> "Task":
        """Returns a fresh unexecuted clone of this task for reproducible runs across policies."""
        return Task(
            task_id=self.task_id,
            arrival_time=self.arrival_time,
            burst_time=self.burst_time,
            tag=self.tag,
        )

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "remaining_time": self.remaining_time,
            "state": self.state.value,
            "assigned_core_id": self.assigned_core_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "waiting_time": self.waiting_time,
            "response_time": self.response_time,
            "turnaround_time": self.turnaround_time,
            "tag": self.tag,
        }
