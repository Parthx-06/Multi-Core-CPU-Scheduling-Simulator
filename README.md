# Multi-Core CPU Scheduling Simulator: Load Balancing & Predictive Task Migration

A cycle-accurate discrete-event multi-core CPU scheduling simulator studying the performance of **Static Task Distribution (Phase 1 Baseline)** versus **Dynamic Predictive Load Balancing & Task Migration (Phase 2 Proposed Improvement)**.

---

## 📌 Project Overview
- **System Architecture**: Multi-core CPU scheduling simulator with local core ready queues, discrete clock cycles, and real-time telemetry.
- **Phase 1 (Baseline)**: Static task distribution (Round-Robin, Arrival-Time Greedy, Random) with **no task migration**.
- **Phase 2 (Proposed Improvement)**: Dynamic load balancing using **Core Load Predictor** (queue gradient + execution rate forecasting) and **Migration Controller** with realistic cache penalty modeling.
- **Workload Profiles**:
  1. `Balanced`: Homogeneous burst times ($\mu=12, \sigma=3$) with regular arrivals.
  2. `Skewed Hotspot`: Every 4th task has 6x burst time, causing extreme bottlenecking on Core 0 under Round-Robin.
  3. `Skewed Bimodal`: 80% light tasks ("mouse") and 20% heavy tasks ("elephant") with bursty arrivals.

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
7. **Migration Cost**: Total tasks migrated and cumulative context switch overhead ticks.

---

## 🔬 Experimental Results: Phase 1 (Static) vs. Phase 2 (Dynamic Predictive)

Direct head-to-head comparison on a **4-Core CPU** under the **Skewed Hotspot Workload**:

| Metric | Phase 1: Static Baseline (RR) | Phase 2: Dynamic Predictive | Scientific Improvement |
| :--- | :---: | :---: | :---: |
| **Makespan (Execution Time)** | **724 ticks** | **300 ticks** | **-58.6% faster execution!** |
| **Speedup (vs 1-Core)** | **1.49x** | **3.60x** | **+2.11x speedup boost** |
| **Multi-Core Efficiency** | **37.3%** | **90.1%** | **+52.8% hardware utilization** |
| **Load Imbalance ($\sigma$)** | **260.7 ticks** | **6.5 ticks** | **-97.5% load variance drop** |
| **Jain's Fairness Index** | **0.516** (Severe skew) | **1.000** (Perfect balance) | **+0.483 fairness restored** |
| **P95 Response Latency** | **461.0 ticks** | **155.0 ticks** | **-66.4% tail latency drop** |
| **Average CPU Utilization** | **37.2%** | **95.4%** | **Idle waste eliminated** |
| **Dynamic Migrations** | **0 (Static)** | **67 tasks migrated** | Overhead: 67 ticks |

### Core Busy Cycles Breakdown:
- **Phase 1 (Static)**: Core 0 = **721 t (99.6%)**, Core 1 = 117 t, Core 2 = 112 t, Core 3 = 128 t. *(Cores 1–3 idle for 600+ ticks!)*
- **Phase 2 (Dynamic)**: Core 0 = **283 t**, Core 1 = **297 t**, Core 2 = **285 t**, Core 3 = **280 t**. *(Near perfect work distribution!)*

---

## 🚀 How to Run the Project

### 1. Run Phase 2 Comparative Benchmark (CLI)
```bash
python run_phase2.py
```
Outputs side-by-side formatted Rich tables for Balanced, Skewed Hotspot, and Skewed Bimodal workloads.

### 2. Run Phase 1 Baseline Benchmark (CLI)
```bash
python run_phase1.py
```

### 3. Run Automated Unit Tests (Pytest)
```bash
python -m pytest tests/
```
Runs 8 automated unit tests verifying core execution, static distribution, predictive modeling, and migration invariants.

### 4. Launch the Interactive Web Dashboard
```bash
python web/server.py
```
Open **`http://127.0.0.1:5000`** in your browser:
- Switch between **Phase 1 (Static)** and **Phase 2 (Dynamic Predictive)**.
- Observe **Migrated Tasks** highlighted as purple glowing blocks in the Gantt timeline.
- Inspect stacked **Busy vs Idle** bar charts and **Queue Dynamics** line graphs.
- Review the **Head-to-Head Comparison Table**.

---

## 📚 Detailed Documentation
- [`PHASE1_GUIDE.md`](file:///c:/Users/parth/OneDrive/Documents/OS_2/PHASE1_GUIDE.md): In-depth guide for Phase 1 in Hinglish + English.
- [`PHASE2_GUIDE.md`](file:///c:/Users/parth/OneDrive/Documents/OS_2/PHASE2_GUIDE.md): In-depth guide for Phase 2 in Hinglish + English covering mathematical equations, work stealing, and numerical proofs.
