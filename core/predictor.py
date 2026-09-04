from collections import deque
from typing import List, Dict, Tuple, Optional
from .core import CPUCore


class CoreLoadPredictor:
    """
    AI / Adaptive Heuristic Predictor:
    Predicts future core load using recent queue lengths, pending burst demand,
    and historical execution rates to detect load imbalance before severe latency occurs.
    """
    def __init__(self, window_size: int = 10, alpha: float = 0.6, beta: float = 0.8):
        self.window_size: int = window_size
        self.alpha: float = alpha  # Weight for queue gradient
        self.beta: float = beta    # Weight for execution rate completion
        
        # History buffers per core: core_id -> deque of records
        self.history: Dict[int, deque] = {}

    def update(self, current_tick: int, cores: List[CPUCore]) -> None:
        """Updates rolling history of queue lengths and core execution states."""
        for core in cores:
            if core.core_id not in self.history:
                self.history[core.core_id] = deque(maxlen=self.window_size)
            
            self.history[core.core_id].append({
                "tick": current_tick,
                "queue_len": core.queue_length,
                "pending_burst": core.total_pending_burst,
                "is_busy": 1 if core.current_task is not None else 0,
            })

    def predict_future_load(self, core: CPUCore, horizon: int = 10) -> float:
        """
        Predicts future computational load (cycles) at horizon H:
        L_hat(t + H) = PendingBurst(t) + alpha * DeltaQueue * H - beta * ExecRate * H
        """
        cid = core.core_id
        hist = self.history.get(cid)
        current_pending = float(core.total_pending_burst)

        if not hist or len(hist) < 2:
            return current_pending

        # 1. Calculate queue trend (gradient)
        first_entry = hist[0]
        last_entry = hist[-1]
        delta_ticks = max(1, last_entry["tick"] - first_entry["tick"])
        queue_velocity = (last_entry["queue_len"] - first_entry["queue_len"]) / delta_ticks

        # 2. Calculate execution rate (busy fraction over window)
        busy_samples = sum(item["is_busy"] for item in hist)
        exec_rate = busy_samples / len(hist)  # Cycles completed per tick (approx 0.0 to 1.0)

        # 3. Forecast future load
        predicted_load = (
            current_pending
            + (self.alpha * queue_velocity * horizon * 5.0)  # Convert queue items to expected cycles
            - (self.beta * exec_rate * horizon)
        )

        return max(0.0, predicted_load)

    def detect_imbalance(
        self, cores: List[CPUCore], threshold: float = 20.0, horizon: int = 10
    ) -> Tuple[bool, Optional[CPUCore], Optional[CPUCore], float]:
        """
        Evaluates predicted core loads and detects if migration is needed.
        Returns:
            (should_migrate, donor_core, recipient_core, predicted_disparity)
        """
        if not cores or len(cores) < 2:
            return False, None, None, 0.0

        # Calculate predicted load for all cores
        predicted_loads = {c.core_id: self.predict_future_load(c, horizon) for c in cores}
        
        # Sort cores by predicted load
        sorted_cores = sorted(cores, key=lambda c: predicted_loads[c.core_id])
        min_core = sorted_cores[0]   # Candidate recipient
        max_core = sorted_cores[-1]  # Candidate donor

        disparity = predicted_loads[max_core.core_id] - predicted_loads[min_core.core_id]

        # Condition 1: Donor must have tasks in its ready queue waiting to run
        if max_core.queue_length == 0:
            # Check if any other core has queued tasks that can be shared
            eligible_donors = [c for c in reversed(sorted_cores) if c.queue_length > 0]
            if not eligible_donors:
                return False, None, None, 0.0
            max_core = eligible_donors[0]
            disparity = predicted_loads[max_core.core_id] - predicted_loads[min_core.core_id]

        # Condition 2: Imbalance exceeds threshold OR idle core work stealing with significant disparity
        is_idle_stealing = (min_core.total_pending_burst == 0 and max_core.queue_length >= 2 and disparity >= 10.0)
        if disparity >= threshold or is_idle_stealing:
            return True, max_core, min_core, disparity

        return False, None, None, disparity

    def reset(self) -> None:
        """Clear prediction histories."""
        self.history.clear()
