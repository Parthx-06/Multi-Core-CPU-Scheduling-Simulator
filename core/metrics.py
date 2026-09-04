import math
from typing import List, Dict, Any, Optional
from .core import CPUCore
from .task import Task


class MetricsEngine:
    @staticmethod
    def calculate_metrics(
        simulation_result: Dict[str, Any],
        single_core_makespan: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Computes all evaluation metrics from a completed simulation run:
        - Load Imbalance (Std Dev, Jain's Fairness Index, Peak-to-Average ratio)
        - Speedup & Efficiency (relative to single-core baseline)
        - Throughput
        - Response Time, Turnaround Time, Waiting Time statistics
        - Per-core and Average CPU Utilization
        """
        makespan: int = simulation_result["makespan"]
        num_cores: int = simulation_result["num_cores"]
        policy: str = simulation_result["policy"]
        cores: List[CPUCore] = simulation_result["cores"]
        tasks: List[Task] = simulation_result["completed_tasks"]

        total_tasks = len(tasks)
        if total_tasks == 0 or makespan == 0:
            return {}

        # Core loads (busy ticks)
        busy_times = [c.total_busy_ticks for c in cores]
        idle_times = [c.total_idle_ticks for c in cores]
        total_work = sum(busy_times)
        avg_busy = total_work / num_cores
        max_busy = max(busy_times) if busy_times else 0
        min_busy = min(busy_times) if busy_times else 0

        # 1. Load Imbalance Metrics
        variance = sum((b - avg_busy) ** 2 for b in busy_times) / num_cores
        std_dev = math.sqrt(variance)
        
        sum_sq = sum(b ** 2 for b in busy_times)
        jains_index = (total_work ** 2) / (num_cores * sum_sq) if sum_sq > 0 else 1.0
        peak_to_avg = (max_busy / avg_busy) if avg_busy > 0 else 1.0
        imbalance_ratio = ((max_busy - min_busy) / max_busy * 100.0) if max_busy > 0 else 0.0

        # 2. CPU Utilization
        core_utilizations = [
            round((b / makespan) * 100.0, 2) if makespan > 0 else 0.0
            for b in busy_times
        ]
        avg_utilization = round(sum(core_utilizations) / num_cores, 2)

        # 3. Throughput (tasks per 100 simulation ticks)
        throughput = round((total_tasks / makespan) * 100.0, 3)

        # 4. Task Timing Statistics (Response, Turnaround, Waiting)
        def compute_stats(values: List[int]) -> Dict[str, float]:
            if not values:
                return {"mean": 0.0, "min": 0, "max": 0, "p95": 0.0}
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            p95_idx = int(0.95 * n)
            p95_idx = min(p95_idx, n - 1)
            return {
                "mean": round(sum(values) / n, 2),
                "min": sorted_vals[0],
                "max": sorted_vals[-1],
                "p95": round(float(sorted_vals[p95_idx]), 2),
            }

        response_times = [t.response_time for t in tasks if t.response_time is not None]
        turnaround_times = [t.turnaround_time for t in tasks if t.turnaround_time is not None]
        waiting_times = [t.waiting_time for t in tasks if t.waiting_time is not None]

        response_stats = compute_stats(response_times)
        turnaround_stats = compute_stats(turnaround_times)
        waiting_stats = compute_stats(waiting_times)

        # 5. Speedup and Efficiency
        speedup = None
        efficiency = None
        if single_core_makespan is not None and makespan > 0:
            speedup = round(single_core_makespan / makespan, 3)
            efficiency = round((speedup / num_cores) * 100.0, 2)

        # 6. Migration Metrics (Phase 2)
        total_migrations = simulation_result.get("total_migrations", 0)
        total_overhead_ticks = sum(c.migration_overhead_ticks for c in cores)

        return {
            "policy": policy,
            "num_cores": num_cores,
            "total_tasks": total_tasks,
            "makespan": makespan,
            "single_core_makespan": single_core_makespan,
            "speedup": speedup,
            "efficiency_pct": efficiency,
            "throughput_per_100_ticks": throughput,
            "migrations": {
                "total_count": total_migrations,
                "total_overhead_ticks": total_overhead_ticks,
                "migrations_in": [c.migrations_in for c in cores],
                "migrations_out": [c.migrations_out for c in cores],
            },
            "load_imbalance": {
                "std_dev_busy_ticks": round(std_dev, 2),
                "jains_fairness_index": round(jains_index, 4),
                "peak_to_avg_ratio": round(peak_to_avg, 3),
                "imbalance_ratio_pct": round(imbalance_ratio, 2),
                "core_busy_ticks": busy_times,
                "core_idle_ticks": idle_times,
            },
            "cpu_utilization": {
                "average_pct": avg_utilization,
                "per_core_pct": core_utilizations,
            },
            "response_time": response_stats,
            "turnaround_time": turnaround_stats,
            "waiting_time": waiting_stats,
        }

    @staticmethod
    def compare_static_vs_dynamic(static_m: Dict[str, Any], dynamic_m: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates direct percentage improvements of Phase 2 Dynamic over Phase 1 Static baseline.
        """
        stat_makespan = static_m.get("makespan", 1)
        dyn_makespan = dynamic_m.get("makespan", 1)
        makespan_reduction_pct = round(((stat_makespan - dyn_makespan) / stat_makespan) * 100.0, 2)

        stat_std = static_m["load_imbalance"]["std_dev_busy_ticks"]
        dyn_std = dynamic_m["load_imbalance"]["std_dev_busy_ticks"]
        imbalance_reduction_pct = round(((stat_std - dyn_std) / stat_std) * 100.0, 2) if stat_std > 0 else 0.0

        stat_jains = static_m["load_imbalance"]["jains_fairness_index"]
        dyn_jains = dynamic_m["load_imbalance"]["jains_fairness_index"]
        fairness_gain = round(dyn_jains - stat_jains, 4)

        stat_p95_resp = static_m["response_time"]["p95"]
        dyn_p95_resp = dynamic_m["response_time"]["p95"]
        p95_resp_reduction_pct = round(((stat_p95_resp - dyn_p95_resp) / stat_p95_resp) * 100.0, 2) if stat_p95_resp > 0 else 0.0

        speedup_gain = round((dynamic_m.get("speedup", 1.0) or 1.0) - (static_m.get("speedup", 1.0) or 1.0), 3)

        return {
            "makespan_reduction_pct": makespan_reduction_pct,
            "imbalance_reduction_pct": imbalance_reduction_pct,
            "fairness_gain": fairness_gain,
            "p95_resp_reduction_pct": p95_resp_reduction_pct,
            "speedup_gain": speedup_gain,
            "total_migrations": dynamic_m["migrations"]["total_count"],
        }
