# Multi-Core CPU Scheduling Simulator: Phase 1 – Baseline Implementation

This project simulates multi-core CPU scheduling and evaluates the performance of **static task distribution** under both **balanced** and **skewed/uneven** workloads.

---

## 📌 Project Overview
- **System Architecture**: Multi-core CPU scheduling simulator with local core queues and cycle-accurate discrete-event clock.
- **Current Phase**: **Phase 1 – Baseline Implementation (Static Task Distribution)**.
- **Static Distribution Policies**:
  1. `Round-Robin Static`: Assigns incoming task $i$ to core $i \pmod M$.
  2. `Arrival Greedy (Min-Pending at Arrival)`: Assigns incoming task to the core with minimal pending workload at arrival tick (strictly *no migration* after assignment).
  3. `Random Static`: Assigns incoming tasks randomly across cores.
- **Workload Profiles**:
  1. `Balanced`: Tasks have homogeneous burst times ($\mu=12, \sigma=3$) with evenly spaced arrival intervals.
  2. `Skewed Hotspot`: Disproportionately heavy tasks (6x burst) cluster on specific cores under static distribution.
  3. `Skewed Bimodal`: 80% light tasks ("mouse") and 20% heavy tasks ("elephant") arriving in bursts.

---

## 📊 Evaluation Metrics
1. **Load Imbalance**:
   - Standard deviation of core busy times: $\sigma = \sqrt{\frac{1}{M}\sum_{i=1}^M (B_i - \bar{B})^2}$
   - Jain's Fairness Index: $J = \frac{(\sum B_i)^2}{M \sum B_i^2}$ ($1.0$ = perfect balance, $<0.7$ = severe imbalance)
   - Peak-to-Average Load Ratio: $\frac{\max(B_i)}{\text{mean}(B_i)}$
2. **Speedup**: $S = \frac{\text{Makespan}_{1\text{-core}}}{\text{Makespan}_{M\text{-cores}}}$
3. **Efficiency**: $E = \frac{S}{M} \times 100\%$
4. **Throughput**: Tasks completed per 100 simulation ticks
5. **Response Time & Turnaround Time**: Mean and 95th percentile (P95)
6. **CPU Utilization**: Per-core percentage and aggregate average utilization

---

## 🚀 How to Run

### 1. Run the CLI Benchmark & Analysis
Run the interactive benchmark script in your terminal:
```bash
python run_phase1.py
```
This runs experiments on 2, 4, and 8 cores comparing Balanced vs. Skewed workloads, printing detailed Rich tables and saving results to `experiments/phase1_benchmark_results.json`.

### 2. Run Automated Unit Tests
```bash
pytest tests/
```

### 3. Launch the Interactive Web Dashboard
```bash
python web/server.py
```
Open your browser at **`http://127.0.0.1:5000`** to:
- Visually inspect the **Core Execution Gantt Timeline** (identifying busy tasks vs idle gaps).
- View **Per-Core Load & Busy vs Idle Distribution** bar charts.
- Observe **Queue Length Dynamics** over time.
- Switch between **Balanced** and **Skewed** workloads interactively.

---

## 🔬 Phase 1 Experimental Findings & Motivation for Phase 2

| Workload | Cores | Policy | Makespan | Speedup | Efficiency | Load Imbalance (StdDev) | Jain's Index | Avg CPU Util |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Balanced** | 4 | Round-Robin | 242 | **3.88x** | **97.1%** | 3.9 ticks | **1.000** | **96.8%** |
| **Balanced** | 4 | Arrival Greedy | 244 | **3.85x** | **96.3%** | 3.3 ticks | **1.000** | **96.4%** |
| **Skewed Hotspot** | 4 | Round-Robin | 724 | **1.49x** | **37.3%** | **260.7 ticks** | **0.516** | **37.2%** |
| **Skewed Hotspot** | 4 | Arrival Greedy | 286 | **3.78x** | **94.5%** | 9.9 ticks | **0.999** | **94.1%** |
| **Skewed Bimodal** | 4 | Round-Robin | 461 | **2.99x** | **74.8%** | 75.6 ticks | **0.954** | **74.7%** |

### Key Takeaway:
Under **Balanced Workloads**, static round-robin scheduling performs near optimally (3.88x speedup on 4 cores, 97.1% efficiency). However, under **Skewed Workloads**, static round-robin degrades catastrophically:
- Makespan jumps from 242 to **724 ticks** (3x slower).
- Core 0 is 99.6% busy while Cores 1–3 sit idle for over 80% of the time.
- Jain's Fairness Index collapses to **0.516**.
- **Phase 2 Improvement**: We will implement dynamic load balancing with future load prediction / adaptive heuristics to migrate queued tasks from overloaded cores to idle cores before severe bottlenecks occur.
