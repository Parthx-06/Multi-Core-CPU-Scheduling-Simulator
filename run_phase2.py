import sys
import os
import json

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from core.scheduler import StaticScheduler, StaticPolicy
from core.dynamic_scheduler import DynamicScheduler
from core.metrics import MetricsEngine
from core.workload import WorkloadGenerator

console = Console()


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]Multi-Core CPU Scheduling Simulator[/bold cyan]\n"
        "[bold green]Phase 2: Proposed Improvement - Predictive Dynamic Load Balancing & Task Migration[/bold green]\n"
        "[dim]Direct Side-by-Side Comparison: Phase 1 (Static Baseline) vs. Phase 2 (Dynamic Predictive)[/dim]",
        border_style="green"
    ))


def display_comparison_table(title: str, static_m: dict, dynamic_m: dict, comparison: dict):
    table = Table(title=title, box=box.ROUNDED, header_style="bold magenta")
    table.add_column("Evaluation Metric", style="cyan", justify="left")
    table.add_column("Phase 1 (Static RR)", justify="right", style="red")
    table.add_column("Phase 2 (Dynamic Predictive)", justify="right", style="green")
    table.add_column("Improvement / Delta", justify="right", style="bold yellow")

    # Makespan
    s_ms = static_m["makespan"]
    d_ms = dynamic_m["makespan"]
    table.add_row("Makespan (Total Ticks)", f"{s_ms} t", f"{d_ms} t", f"-{comparison['makespan_reduction_pct']:.1f}%")

    # Speedup
    s_sp = static_m.get("speedup", 1.0) or 1.0
    d_sp = dynamic_m.get("speedup", 1.0) or 1.0
    table.add_row("Speedup (vs 1-Core)", f"{s_sp:.2f}x", f"{d_sp:.2f}x", f"+{comparison['speedup_gain']:.2f}x")

    # Efficiency
    s_eff = static_m.get("efficiency_pct", 100.0) or 100.0
    d_eff = dynamic_m.get("efficiency_pct", 100.0) or 100.0
    eff_delta = d_eff - s_eff
    table.add_row("Efficiency (%)", f"{s_eff:.1f}%", f"{d_eff:.1f}%", f"+{eff_delta:.1f}%")

    # Load Imbalance StdDev
    s_std = static_m["load_imbalance"]["std_dev_busy_ticks"]
    d_std = dynamic_m["load_imbalance"]["std_dev_busy_ticks"]
    table.add_row("Load Imbalance (StdDev)", f"{s_std:.1f}", f"{d_std:.1f}", f"-{comparison['imbalance_reduction_pct']:.1f}%")

    # Jain's Fairness Index
    s_j = static_m["load_imbalance"]["jains_fairness_index"]
    d_j = dynamic_m["load_imbalance"]["jains_fairness_index"]
    table.add_row("Jain's Fairness Index", f"{s_j:.3f}", f"{d_j:.3f}", f"+{comparison['fairness_gain']:.3f}")

    # Avg Response Time
    s_rt = static_m["response_time"]["mean"]
    d_rt = dynamic_m["response_time"]["mean"]
    table.add_row("Avg Response Time", f"{s_rt:.1f} t", f"{d_rt:.1f} t", f"{d_rt - s_rt:+.1f} t")

    # P95 Response Time
    s_p95 = static_m["response_time"]["p95"]
    d_p95 = dynamic_m["response_time"]["p95"]
    table.add_row("P95 Response Time", f"{s_p95:.1f} t", f"{d_p95:.1f} t", f"-{comparison['p95_resp_reduction_pct']:.1f}%")

    # CPU Utilization
    s_util = static_m["cpu_utilization"]["average_pct"]
    d_util = dynamic_m["cpu_utilization"]["average_pct"]
    table.add_row("Avg CPU Utilization", f"{s_util:.1f}%", f"{d_util:.1f}%", f"{d_util - s_util:+.1f}%")

    # Migrations
    mig_count = dynamic_m["migrations"]["total_count"]
    overhead = dynamic_m["migrations"]["total_overhead_ticks"]
    table.add_row("Dynamic Task Migrations", "0 (Static)", f"{mig_count} tasks", f"Overhead: {overhead} t")

    console.print(table)


def run_phase2_benchmarks():
    print_banner()

    repo_dir = os.path.dirname(os.path.abspath(__file__))
    preset_dir = os.path.join(repo_dir, "experiments", "presets")
    hotspot_path = os.path.join(preset_dir, "skewed_hotspot.json")
    bimodal_path = os.path.join(preset_dir, "skewed_bimodal.json")
    balanced_path = os.path.join(preset_dir, "balanced.json")

    # Ensure presets exist
    if not os.path.exists(hotspot_path):
        from experiments.benchmark_runner import BenchmarkRunner
        BenchmarkRunner(output_dir=preset_dir).generate_and_save_standard_presets()

    all_comparison_results = {}

    # 1. Experiment 1: Skewed Hotspot Workload (4 Cores)
    console.print("\n[bold red]=== Experiment 1: Skewed Hotspot Workload (4 Cores) ===[/bold red]")
    console.print("[dim]Where Phase 1 suffered severe Core 0 bottleneck (724 ticks makespan, 37% efficiency)[/dim]")
    tasks_hotspot = WorkloadGenerator.load_workload_from_json(hotspot_path)
    
    # 1-core baseline for speedup
    s1 = StaticScheduler(num_cores=1, policy=StaticPolicy.ROUND_ROBIN).run(tasks_hotspot)
    base_makespan = s1["makespan"]

    # Phase 1: Static Round-Robin
    static_res_hotspot = StaticScheduler(num_cores=4, policy=StaticPolicy.ROUND_ROBIN).run(tasks_hotspot)
    static_m_hotspot = MetricsEngine.calculate_metrics(static_res_hotspot, single_core_makespan=base_makespan)

    # Phase 2: Dynamic Predictive Scheduler
    dyn_res_hotspot = DynamicScheduler(
        num_cores=4,
        initial_policy=StaticPolicy.ROUND_ROBIN,
        imbalance_threshold=15.0,
        prediction_horizon=10,
        check_interval=2,
        migration_penalty=1
    ).run(tasks_hotspot)
    dyn_m_hotspot = MetricsEngine.calculate_metrics(dyn_res_hotspot, single_core_makespan=base_makespan)

    comp_hotspot = MetricsEngine.compare_static_vs_dynamic(static_m_hotspot, dyn_m_hotspot)
    display_comparison_table("Skewed Hotspot: Phase 1 (Static) vs. Phase 2 (Dynamic)", static_m_hotspot, dyn_m_hotspot, comp_hotspot)

    # Per Core Loads Comparison
    console.print(f"[bold]Core Busy Ticks Breakdown under Skewed Hotspot:[/bold]")
    console.print(f"  Phase 1 (Static) : Core 0=[red]{static_m_hotspot['load_imbalance']['core_busy_ticks'][0]}[/red] t, "
                  f"Core 1={static_m_hotspot['load_imbalance']['core_busy_ticks'][1]} t, "
                  f"Core 2={static_m_hotspot['load_imbalance']['core_busy_ticks'][2]} t, "
                  f"Core 3={static_m_hotspot['load_imbalance']['core_busy_ticks'][3]} t")
    console.print(f"  Phase 2 (Dynamic): Core 0=[green]{dyn_m_hotspot['load_imbalance']['core_busy_ticks'][0]}[/green] t, "
                  f"Core 1=[green]{dyn_m_hotspot['load_imbalance']['core_busy_ticks'][1]}[/green] t, "
                  f"Core 2=[green]{dyn_m_hotspot['load_imbalance']['core_busy_ticks'][2]}[/green] t, "
                  f"Core 3=[green]{dyn_m_hotspot['load_imbalance']['core_busy_ticks'][3]}[/green] t")
    console.print(f"  [cyan]-> Dynamic scheduler migrated {dyn_res_hotspot['total_migrations']} tasks from overloaded Core 0 to idle cores![/cyan]\n")

    # 2. Experiment 2: Skewed Bimodal Workload (Elephant & Mouse) (4 Cores)
    console.print("[bold yellow]=== Experiment 2: Skewed Bimodal Workload (4 Cores) ===[/bold yellow]")
    tasks_bimodal = WorkloadGenerator.load_workload_from_json(bimodal_path)
    s1_bi = StaticScheduler(num_cores=1, policy=StaticPolicy.ROUND_ROBIN).run(tasks_bimodal)
    base_makespan_bi = s1_bi["makespan"]

    static_res_bi = StaticScheduler(num_cores=4, policy=StaticPolicy.ROUND_ROBIN).run(tasks_bimodal)
    static_m_bi = MetricsEngine.calculate_metrics(static_res_bi, single_core_makespan=base_makespan_bi)

    dyn_res_bi = DynamicScheduler(
        num_cores=4,
        initial_policy=StaticPolicy.ROUND_ROBIN,
        imbalance_threshold=15.0,
        prediction_horizon=10,
        check_interval=2,
        migration_penalty=1
    ).run(tasks_bimodal)
    dyn_m_bi = MetricsEngine.calculate_metrics(dyn_res_bi, single_core_makespan=base_makespan_bi)

    comp_bi = MetricsEngine.compare_static_vs_dynamic(static_m_bi, dyn_m_bi)
    display_comparison_table("Skewed Bimodal: Phase 1 (Static) vs. Phase 2 (Dynamic)", static_m_bi, dyn_m_bi, comp_bi)

    # 3. Experiment 3: Balanced Workload (4 Cores)
    console.print("\n[bold green]=== Experiment 3: Balanced Workload (4 Cores) ===[/bold green]")
    console.print("[dim]Verifying that predictive dynamic migration incurs near-zero overhead when already balanced[/dim]")
    tasks_balanced = WorkloadGenerator.load_workload_from_json(balanced_path)
    s1_bal = StaticScheduler(num_cores=1, policy=StaticPolicy.ROUND_ROBIN).run(tasks_balanced)
    base_makespan_bal = s1_bal["makespan"]

    static_res_bal = StaticScheduler(num_cores=4, policy=StaticPolicy.ROUND_ROBIN).run(tasks_balanced)
    static_m_bal = MetricsEngine.calculate_metrics(static_res_bal, single_core_makespan=base_makespan_bal)

    dyn_res_bal = DynamicScheduler(
        num_cores=4,
        initial_policy=StaticPolicy.ROUND_ROBIN,
        imbalance_threshold=15.0,
        prediction_horizon=10,
        check_interval=2,
        migration_penalty=1
    ).run(tasks_balanced)
    dyn_m_bal = MetricsEngine.calculate_metrics(dyn_res_bal, single_core_makespan=base_makespan_bal)

    comp_bal = MetricsEngine.compare_static_vs_dynamic(static_m_bal, dyn_m_bal)
    display_comparison_table("Balanced Workload: Phase 1 (Static) vs. Phase 2 (Dynamic)", static_m_bal, dyn_m_bal, comp_bal)

    # Save results to JSON
    all_comparison_results = {
        "skewed_hotspot": {
            "static": static_m_hotspot,
            "dynamic": dyn_m_hotspot,
            "comparison": comp_hotspot,
            "migrations": dyn_res_hotspot["migrations"][:20],
        },
        "skewed_bimodal": {
            "static": static_m_bi,
            "dynamic": dyn_m_bi,
            "comparison": comp_bi,
        },
        "balanced": {
            "static": static_m_bal,
            "dynamic": dyn_m_bal,
            "comparison": comp_bal,
        }
    }

    output_file = os.path.join(repo_dir, "experiments", "phase2_comparison_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_comparison_results, f, indent=2)

    console.print(f"\n[bold green][OK] Phase 2 Dynamic Benchmark Complete![/bold green]")
    console.print(f"[cyan]Results saved to: {output_file}[/cyan]\n")

    # Conclusion Banner
    console.print(Panel(
        f"[bold green]Phase 2 Proposed Improvement Highlights:[/bold green]\n\n"
        f"1. [b]Makespan slashed by {comp_hotspot['makespan_reduction_pct']:.1f}%[/b] under skewed hotspot (from {static_m_hotspot['makespan']} t down to {dyn_m_hotspot['makespan']} t)!\n"
        f"2. [b]Speedup boosted from {static_m_hotspot['speedup']:.2f}x to {dyn_m_hotspot['speedup']:.2f}x[/b], recovering multi-core utilization to {dyn_m_hotspot['cpu_utilization']['average_pct']:.1f}%!\n"
        f"3. [b]Jain's Fairness Index restored from {static_m_hotspot['load_imbalance']['jains_fairness_index']:.3f} to {dyn_m_hotspot['load_imbalance']['jains_fairness_index']:.3f}[/b]!\n"
        f"4. [b]P95 Response Latency dropped by {comp_hotspot['p95_resp_reduction_pct']:.1f}%[/b] (from {static_m_hotspot['response_time']['p95']:.1f} t to {dyn_m_hotspot['response_time']['p95']:.1f} t)!\n"
        f"5. [b]Adaptive Stability[/b]: When the workload is already balanced, the predictor avoids thrashing ({dyn_res_bal['total_migrations']} unnecessary migrations).",
        title="Phase 2 Achievement Summary",
        border_style="green"
    ))


if __name__ == "__main__":
    run_phase2_benchmarks()
