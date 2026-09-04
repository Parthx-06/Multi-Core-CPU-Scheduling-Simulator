import os
import json
from typing import Dict, List, Any
from core.task import Task
from core.scheduler import StaticScheduler, StaticPolicy
from core.metrics import MetricsEngine
from core.workload import WorkloadGenerator


class BenchmarkRunner:
    def __init__(self, output_dir: str = "experiments/presets"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_and_save_standard_presets(self, num_tasks: int = 80, seed: int = 42) -> Dict[str, str]:
        """Generates standard benchmark workloads and saves them for reproducible evaluation."""
        presets = {
            "balanced": WorkloadGenerator.generate_balanced_workload(
                num_tasks=num_tasks, mean_burst=12, burst_variance=3, arrival_interval=2, seed=seed
            ),
            "skewed_hotspot": WorkloadGenerator.generate_skewed_hotspot_workload(
                num_tasks=num_tasks, normal_burst=6, hotspot_burst=36, target_core_index=0, num_cores=4, seed=seed
            ),
            "skewed_bimodal": WorkloadGenerator.generate_skewed_bimodal_workload(
                num_tasks=num_tasks, heavy_ratio=0.20, light_burst_range=(3, 7), heavy_burst_range=(35, 60), seed=seed
            ),
        }

        paths = {}
        for name, tasks in presets.items():
            path = os.path.join(self.output_dir, f"{name}.json")
            WorkloadGenerator.save_workload_to_json(tasks, path)
            paths[name] = path

        return paths

    def run_workload_comparison(
        self,
        workload_tasks: List[Task],
        workload_name: str,
        core_counts: List[int] = [2, 4, 8],
        policies: List[StaticPolicy] = [StaticPolicy.ROUND_ROBIN, StaticPolicy.ARRIVAL_GREEDY],
    ) -> Dict[str, Any]:
        """
        Runs comprehensive benchmark for a given workload across core counts and static policies.
        Calculates speedup and efficiency relative to single-core execution.
        """
        # 1. Single core baseline (to compute Speedup & Efficiency)
        single_core_scheduler = StaticScheduler(num_cores=1, policy=StaticPolicy.ROUND_ROBIN)
        single_res = single_core_scheduler.run(workload_tasks)
        single_core_makespan = single_res["makespan"]

        results = {
            "workload_name": workload_name,
            "total_tasks": len(workload_tasks),
            "single_core_makespan": single_core_makespan,
            "runs": []
        }

        for num_cores in core_counts:
            for policy in policies:
                scheduler = StaticScheduler(num_cores=num_cores, policy=policy)
                sim_res = scheduler.run(workload_tasks)
                metrics = MetricsEngine.calculate_metrics(sim_res, single_core_makespan=single_core_makespan)
                
                # Include timeline snippet for visualizer
                core_timelines = {
                    f"core_{c.core_id}": c.timeline
                    for c in sim_res["cores"]
                }
                
                results["runs"].append({
                    "workload": workload_name,
                    "policy": policy.value,
                    "num_cores": num_cores,
                    "metrics": metrics,
                    "core_timelines": core_timelines,
                })

        return results

    def run_all_phase1_benchmarks(self) -> Dict[str, Any]:
        """Runs benchmarks on Balanced, Hotspot Skewed, and Bimodal Skewed workloads."""
        preset_paths = self.generate_and_save_standard_presets()
        all_results = {}

        for workload_name, path in preset_paths.items():
            tasks = WorkloadGenerator.load_workload_from_json(path)
            all_results[workload_name] = self.run_workload_comparison(
                workload_tasks=tasks,
                workload_name=workload_name,
                core_counts=[2, 4, 8],
                policies=[StaticPolicy.ROUND_ROBIN, StaticPolicy.ARRIVAL_GREEDY]
            )

        # Save results to JSON
        output_file = os.path.join("experiments", "phase1_benchmark_results.json")
        
        # Strip or condense timelines for the compact summary file
        compact_results = {}
        for w_name, w_data in all_results.items():
            compact_results[w_name] = {
                "workload_name": w_data["workload_name"],
                "total_tasks": w_data["total_tasks"],
                "single_core_makespan": w_data["single_core_makespan"],
                "runs": [
                    {
                        "workload": r["workload"],
                        "policy": r["policy"],
                        "num_cores": r["num_cores"],
                        "metrics": r["metrics"],
                    }
                    for r in w_data["runs"]
                ]
            }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(compact_results, f, indent=2)

        return all_results
