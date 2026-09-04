import json
import random
from typing import List, Dict, Any
from .task import Task


class WorkloadGenerator:
    @staticmethod
    def generate_balanced_workload(
        num_tasks: int = 60,
        mean_burst: int = 12,
        burst_variance: int = 3,
        arrival_interval: int = 2,
        seed: int = 42
    ) -> List[Task]:
        """
        Generates a balanced workload where task execution times are evenly distributed
        and arrivals occur at regular intervals.
        """
        rng = random.Random(seed)
        tasks: List[Task] = []
        current_arrival = 0

        for i in range(num_tasks):
            # Arrival time progression
            gap = max(0, rng.randint(arrival_interval - 1, arrival_interval + 1))
            current_arrival += gap
            
            # Homogeneous burst times
            burst = max(1, int(rng.gauss(mean_burst, burst_variance)))
            
            tasks.append(Task(
                task_id=i + 1,
                arrival_time=current_arrival,
                burst_time=burst,
                tag="normal"
            ))

        return tasks

    @staticmethod
    def generate_skewed_hotspot_workload(
        num_tasks: int = 60,
        normal_burst: int = 6,
        hotspot_burst: int = 35,
        target_core_index: int = 0,
        num_cores: int = 4,
        seed: int = 42
    ) -> List[Task]:
        """
        Generates a skewed workload specifically highlighting the weakness of static Round-Robin:
        Tasks that round-robin to a particular core (target_core_index) are assigned
        disproportionately massive burst times ("hotspot").
        """
        rng = random.Random(seed)
        tasks: List[Task] = []
        current_arrival = 0

        for i in range(num_tasks):
            current_arrival += rng.randint(1, 3)
            
            # If this task index matches target core under Round Robin
            if i % num_cores == target_core_index:
                burst = hotspot_burst + rng.randint(-3, 5)
                tag = "heavy"
            else:
                burst = max(2, normal_burst + rng.randint(-2, 2))
                tag = "light"

            tasks.append(Task(
                task_id=i + 1,
                arrival_time=current_arrival,
                burst_time=burst,
                tag=tag
            ))

        return tasks

    @staticmethod
    def generate_skewed_bimodal_workload(
        num_tasks: int = 60,
        heavy_ratio: float = 0.20,
        light_burst_range: tuple = (3, 6),
        heavy_burst_range: tuple = (30, 50),
        seed: int = 42
    ) -> List[Task]:
        """
        Generates a bimodal (elephant and mouse) workload:
        - 80% light tasks
        - 20% heavy elephant tasks
        Arrivals arrive in randomized clusters, creating severe queue variance under static mapping.
        """
        rng = random.Random(seed)
        tasks: List[Task] = []
        current_arrival = 0

        for i in range(num_tasks):
            # Clustered arrivals
            current_arrival += rng.choice([0, 1, 1, 2, 4])
            
            is_heavy = rng.random() < heavy_ratio
            if is_heavy:
                burst = rng.randint(*heavy_burst_range)
                tag = "heavy"
            else:
                burst = rng.randint(*light_burst_range)
                tag = "light"

            tasks.append(Task(
                task_id=i + 1,
                arrival_time=current_arrival,
                burst_time=burst,
                tag=tag
            ))

        return tasks

    @staticmethod
    def save_workload_to_json(tasks: List[Task], file_path: str) -> None:
        """Serializes workload to JSON file for reproducible experiments."""
        data = [
            {
                "task_id": t.task_id,
                "arrival_time": t.arrival_time,
                "burst_time": t.burst_time,
                "tag": t.tag,
            }
            for t in tasks
        ]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_workload_from_json(file_path: str) -> List[Task]:
        """Loads workload from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            Task(
                task_id=item["task_id"],
                arrival_time=item["arrival_time"],
                burst_time=item["burst_time"],
                tag=item.get("tag", "normal")
            )
            for item in data
        ]
