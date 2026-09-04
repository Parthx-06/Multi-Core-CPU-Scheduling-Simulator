import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from core.task import Task
from core.scheduler import StaticScheduler, StaticPolicy
from core.dynamic_scheduler import DynamicScheduler
from core.metrics import MetricsEngine
from core.workload import WorkloadGenerator
from experiments.benchmark_runner import BenchmarkRunner

app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/benchmarks", methods=["GET"])
def get_benchmarks():
    benchmark_file = os.path.join(PROJECT_ROOT, "experiments", "phase1_benchmark_results.json")
    if not os.path.exists(benchmark_file):
        runner = BenchmarkRunner(output_dir=os.path.join(PROJECT_ROOT, "experiments", "presets"))
        runner.run_all_phase1_benchmarks()

    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/phase2_comparison", methods=["GET"])
def get_phase2_comparison():
    comp_file = os.path.join(PROJECT_ROOT, "experiments", "phase2_comparison_results.json")
    if not os.path.exists(comp_file):
        import run_phase2
        run_phase2.run_phase2_benchmarks()

    with open(comp_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)


@app.route("/api/simulate", methods=["POST"])
def run_simulation():
    body = request.get_json() or {}
    workload_type = body.get("workload_type", "skewed_hotspot")
    num_cores = int(body.get("num_cores", 4))
    num_tasks = int(body.get("num_tasks", 60))
    policy_str = body.get("policy", "round_robin")
    scheduler_mode = body.get("scheduler_mode", "dynamic")  # "static" or "dynamic"
    threshold = float(body.get("imbalance_threshold", 15.0))
    horizon = int(body.get("prediction_horizon", 10))
    penalty = int(body.get("migration_penalty", 1))
    seed = int(body.get("seed", 42))

    # Map policy
    if policy_str == "arrival_greedy":
        policy = StaticPolicy.ARRIVAL_GREEDY
    elif policy_str == "random":
        policy = StaticPolicy.RANDOM
    else:
        policy = StaticPolicy.ROUND_ROBIN

    # Generate workload
    if workload_type == "balanced":
        tasks = WorkloadGenerator.generate_balanced_workload(
            num_tasks=num_tasks, mean_burst=12, burst_variance=3, arrival_interval=2, seed=seed
        )
    elif workload_type == "skewed_bimodal":
        tasks = WorkloadGenerator.generate_skewed_bimodal_workload(
            num_tasks=num_tasks, heavy_ratio=0.20, light_burst_range=(3, 7), heavy_burst_range=(35, 60), seed=seed
        )
    else:  # skewed_hotspot
        tasks = WorkloadGenerator.generate_skewed_hotspot_workload(
            num_tasks=num_tasks, normal_burst=6, hotspot_burst=36, target_core_index=0, num_cores=num_cores, seed=seed
        )

    # 1-core baseline for speedup
    single_scheduler = StaticScheduler(num_cores=1, policy=StaticPolicy.ROUND_ROBIN, seed=seed)
    single_res = single_scheduler.run(tasks)
    single_core_makespan = single_res["makespan"]

    # Target multi-core simulation
    if scheduler_mode == "dynamic":
        scheduler = DynamicScheduler(
            num_cores=num_cores,
            initial_policy=policy,
            imbalance_threshold=threshold,
            prediction_horizon=horizon,
            check_interval=2,
            migration_penalty=penalty,
            seed=seed,
        )
    else:
        scheduler = StaticScheduler(num_cores=num_cores, policy=policy, seed=seed)

    sim_res = scheduler.run(tasks)
    metrics = MetricsEngine.calculate_metrics(sim_res, single_core_makespan=single_core_makespan)

    # Core execution timelines (sampled if large)
    timeline_data = {
        f"core_{c.core_id}": c.timeline[:1200]  # Limit to 1200 ticks for UI rendering performance
        for c in sim_res["cores"]
    }

    task_summary = [t.to_dict() for t in sim_res["completed_tasks"][:100]]
    migrations = sim_res.get("migrations", [])

    return jsonify({
        "workload_type": workload_type,
        "scheduler_mode": scheduler_mode,
        "num_cores": num_cores,
        "policy": policy.value,
        "metrics": metrics,
        "timelines": timeline_data,
        "tasks": task_summary,
        "migrations": migrations[:50],
    })


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(BASE_DIR, path)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
