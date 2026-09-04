# Phase 2: Complete In-Depth Guide & Analysis (Dynamic Load Balancing & Predictive Task Migration)
### (Hinglish + English Masterclass Documentation)

---

## 📑 Table of Contents
1. [Project Context & Phase 2 Objectives (परिचय और उद्देश्य)](#1-project-context--phase-2-objectives)
2. [Why Phase 1 Failed & What Phase 2 Solves (Phase 1 की नाकामी और Phase 2 का हल)](#2-why-phase-1-failed--what-phase-2-solves)
3. [Phase 2 Architecture & Control Loop Flowchart (सिस्टम का नया आर्किटेक्चर)](#3-phase-2-architecture--control-loop-flowchart)
4. [Deep-Dive into Phase 2 Code Modules](#4-deep-dive-into-phase-2-code-modules)
   - [4.1 Core Load Predictor (`core/predictor.py`)](#41-core-load-predictor-corepredictorpy)
   - [4.2 Dynamic Scheduler & Migration Controller (`core/dynamic_scheduler.py`)](#42-dynamic-scheduler--migration-controller-coredynamicschedulerpy)
   - [4.3 CPUCore Migration Support (`core/core.py`)](#43-cpucore-migration-support-corecorepy)
   - [4.4 Metrics Engine Comparison (`core/metrics.py`)](#44-metrics-engine-comparison-coremetricspy)
5. [The Step-by-Step Life of a Migrated Task (Task #12 ki Kahani)](#5-the-step-by-step-life-of-a-migrated-task)
6. [Real-World Analogies (Bank Manager & Highway Traffic)](#6-real-world-analogies)
7. [How Real-World Operating Systems Do This (Linux CFS vs. Our Model)](#7-how-real-world-operating-systems-do-this)
8. [Mathematical Formulas & Step-by-Step Numerical Walkthrough](#8-mathematical-formulas--step-by-step-numerical-walkthrough)
9. [Benchmark Comparison Table (Phase 1 Static vs. Phase 2 Dynamic)](#9-benchmark-comparison-table-phase-1-vs-phase-2)
10. [Viva / Interview Master Questions & Answers (अक्सर पूछे जाने वाले सवाल)](#10-viva--interview-master-questions--answers)
11. [Web Dashboard Visualizer Guide](#11-web-dashboard-visualizer-guide)
12. [How to Run, Test, and Verify Phase 2](#12-how-to-run-test-and-verify-phase-2)

---

## 1. Project Context & Phase 2 Objectives

### English:
In **Phase 1**, we implemented the baseline multi-core CPU scheduler using **Static Task Distribution**. We proved experimentally that static allocation collapses when workloads are skewed (bottleneck makespan exploded to 724 ticks, multi-core efficiency plummeted to 37.3%, and Jain's fairness dropped to 0.516).

In **Phase 2 (Proposed Improvement)**, we introduce **Dynamic Load Balancing**:
- **AI / Adaptive Predictor Task**: Predict future core load using recent queue lengths, execution velocities, and remaining burst work.
- **Dynamic Migration Controller**: Proactively migrate queued tasks from overloaded cores to less-loaded or idle cores before severe latency accumulates.
- **Migration Penalty Modeling**: Accurately model realistic cache invalidation / context-switch overhead (default: 1 tick) to demonstrate that the scheduler balances load efficiently without thrashing.

### Hinglish (सरल भाषा में):
Phase 1 mein humne dekha tha ki **Static Task Distribution** mein ek baar jo task kisi core ko mil gaya, woh wahi bandha rehta tha. Nateeja yeh nikla ki jab uneven tasks aaye, toh **Core 0 par 721 ticks ka bhari jaam lag gaya**, jabki Core 1, 2, aur 3 lagbhag **600+ ticks tak aaram se khali baithe rahe!**

**Phase 2 ka Main Goal**:
Phase 2 mein hum ek **Intelligent Dynamic Load Balancer** banate hain jo:
1. Cores ki queue lengths aur execution speed ko dekh kar **bhavishya ke load ko predict** karta hai.
2. Jaise hi kisi core par jaam lagne lagta hai ya koi dusra core khali baithta hai, yeh controller automatically tasks ko **overloaded core se idle core par migrate** (transfer) kar deta hai.
3. Isse multi-core CPU ke saare cores milkar barabar kaam karte hain aur total execution time (Makespan) adhe se bhi kam (724 $\to$ 300 ticks) ho jata hai!

---

## 2. Why Phase 1 Failed & What Phase 2 Solves

| Problem in Phase 1 (Static Baseline) | Solution in Phase 2 (Dynamic Predictive) |
| :--- | :--- |
| **1. Blind Placement**: Round-Robin ne bina task size jaane har 4th heavy task Core 0 ko de diya. | **1. Continuous Monitoring**: Predictor har tick par har core ke pending burst aur queue growth ko monitor karta hai. |
| **2. Zero Migration (Live-Lock)**: Core 0 ghanto busy raha jabki Core 1–3 idle baithe rahe. | **2. Work Stealing & Migration**: Idle/underloaded cores overloaded core ke queue tail se tasks ko "steal" karke execute karte hain. |
| **3. Late Imbalance Reaction**: Static policy ko imbalance ka pata hi nahi chalta. | **3. Predictive Horizon ($H$)**: Imbalance aane se *pehle* hi predictor warning signal de deta hai ki Core 0 overload hone wala hai! |
| **4. Latency Explosion**: Chote tasks heavy elephant task ke peeche phanse rahe (P95 Latency = 461 ticks). | **4. Latency Slashed**: Queued tasks dusre cores par shift ho gaye, jisse P95 Response Latency 461 ticks se girkar **155 ticks (-66.4%)** ho gayi! |

---

## 3. Phase 2 Architecture & Control Loop Flowchart

Yeh flowchart dikhata hai ki Phase 2 ka predictive control loop tick-by-tick kaise kaam karta hai:

```
                                    +-----------------------------------------+
                                    |        Arriving Tasks Stream            |
                                    +--------------------+--------------------+
                                                         | Initial Placement (Round Robin / Greedy)
                                                         v
+-------------------------------------------------------------------------------------------------------------+
|                                    DYNAMIC SCHEDULER (`core/dynamic_scheduler.py`)                          |
|                                                                                                             |
|   +-----------------------------------------------------------------------------------------------------+   |
|   |  Predictive Feedback Loop (Every tick / check interval):                                            |   |
|   |                                                                                                     |   |
|   |   1. READ CORE STATES: Q_i(t), PendingBurst_i(t), Busy/Idle States                                  |   |
|   |                           |                                                                         |   |
|   |                           v                                                                         |   |
|   |   2. PREDICTOR (`core/predictor.py`):                                                               |   |
|   |      Calculate Queue Velocity: Delta Q_i / Delta t                                                  |   |
|   |      Calculate Execution Rate: R_i                                                                  |   |
|   |      Forecast Future Load: L_hat_i(t + H)                                                           |   |
|   |                           |                                                                         |   |
|   |                           v                                                                         |   |
|   |   3. IMBALANCE EVALUATOR:                                                                           |   |
|   |      Find Donor Core (Max L_hat) and Recipient Core (Min L_hat)                                     |   |
|   |      Condition: Disparity >= Threshold OR (Recipient is Idle and Donor Queue >= 2)                  |   |
|   |                           |                                                                         |   |
|   |            [ Imbalance Detected? ]                                                                  |   |
|   |                   /         \                                                                       |   |
|   |                 YES          NO --> Continue normal execution                                       |   |
|   |                  |                                                                                  |   |
|   |                  v                                                                                  |   |
|   |   4. DYNAMIC MIGRATION CONTROLLER:                                                                  |   |
|   |      * Donor: Extract ready task from queue tail (anti-thrashing: max_migrations_per_task <= 1)     |   |
|   |      * Apply realistic Cache Penalty (1 tick)                                                       |   |
|   |      * Recipient: Enqueue/execute migrated task                                                     |   |
|   |      * Log migration event {"tick": t, "task": id, "from": C0, "to": C1, "cost": 1}                |   |
|   +-----------------------------------------------------------------------------------------------------+   |
|                                                                                                             |
|   +--------------------+     +--------------------+     +--------------------+     +--------------------+   |
|   |    CPU Core 0      |     |    CPU Core 1      |     |    CPU Core 2      |     |    CPU Core 3      |   |
|   |    (`core.py`)     |     |    (`core.py`)     |     |    (`core.py`)     |     |    (`core.py`)     |   |
|   | Busy: ~283 ticks   |     | Busy: ~297 ticks   |     | Busy: ~285 ticks   |     | Busy: ~280 ticks   |   |
|   +--------------------+     +--------------------+     +--------------------+     +--------------------+   |
+-------------------------------------------------------------------------------------------------------------+
                                                         | Finished Tasks & Migration Logs
                                                         v
+-------------------------------------------------------------------------------------------------------------+
|                                      METRICS ENGINE (`core/metrics.py`)                                     |
|   * Comparative Analysis: Phase 1 vs Phase 2 Delta                                                          |
|   * Makespan: 724 t -> 300 t (-58.6%)  | Speedup: 1.49x -> 3.60x (+2.11x) | Jain's Index: 0.516 -> 1.000   |
+-------------------------------------------------------------------------------------------------------------+
```

---

## 4. Deep-Dive into Phase 2 Code Modules

### 4.1 Core Load Predictor ([`core/predictor.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/predictor.py))

Predictor ka kaam hai **aane wale samay mein core ka load kaisa hoga** yeh pehle se bhanp lena.

#### Mathematical Forecasting Equation:
Har core $i$ ke liye, horizon $H$ ticks aage ka predicted load $\hat{L}_i(t + H)$ is formula se nikalta hai:

$$\hat{L}_i(t + H) = W_i(t) + \alpha \cdot \left(\frac{\Delta Q_i}{\Delta t}\right) \cdot H \cdot \bar{B}_{task} - \beta \cdot R_i(t) \cdot H$$

Jahan:
- $W_i(t)$: Core $i$ ka current pending burst work (current running task + ready queue).
- $\frac{\Delta Q_i}{\Delta t}$: Queue length ka badhne ya ghatne ka gradient (velocity). Agar queue tezi se lambi ho rahi hai, toh future mein heavy bottleneck aayega.
- $\alpha = 0.6$: Queue trend weighting parameter.
- $R_i(t)$: Core ka historical execution rate (cycles completed per tick over window $W=10$).
- $\beta = 0.8$: Completion factor.

#### Imbalance Detection Logic:
1. Har core ka $\hat{L}_i(t+H)$ nikalo.
2. $\text{Donor} = \arg\max(\hat{L}_i)$ (Sabse zyada loaded core).
3. $\text{Recipient} = \arg\min(\hat{L}_j)$ (Sabse kam loaded core).
4. **Disparity** $= \hat{L}_{donor} - \hat{L}_{recipient}$.
5. **Trigger Condition**:
   - Agar $\text{Disparity} \ge \text{Threshold}$ (default 15 cycles) **AND** Donor ke ready queue mein transfer karne layak task ho.
   - **YA PHIR** Recipient core bilkul **idle** ho gaya ho ($W_{recipient} == 0$), Donor ke paas $\ge 2$ tasks ho, aur Disparity $\ge 10.0$ ho.

---

### 4.2 Dynamic Scheduler & Migration Controller ([`core/dynamic_scheduler.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/dynamic_scheduler.py))

`DynamicScheduler` simulation clock ko aage badhata hai aur migration execute karta hai:

```python
def _attempt_migration(self):
    should_migrate, donor, recipient, disparity = self.predictor.detect_imbalance(
        self.cores, threshold=self.imbalance_threshold, horizon=self.prediction_horizon
    )

    if should_migrate and donor is not None and recipient is not None:
        # Donor ke queue ke tail se task nikalo
        migrated_task = donor.extract_task_for_migration()
        if migrated_task is not None:
            # Recipient core ko task transfer karo with penalty
            recipient.receive_migrated_task(migrated_task, penalty_ticks=self.migration_penalty)
            
            # Migration event log karo (for UI and metrics)
            self.migrations.append({
                "tick": self.current_tick,
                "task_id": migrated_task.task_id,
                "from_core": donor.core_id,
                "to_core": recipient.core_id,
                "burst_time": migrated_task.burst_time,
                "penalty_ticks": self.migration_penalty,
            })
```

#### Anti-Thrashing Constraints (Live-Lock Prevention):
Agar dynamic load balancer careless ho, toh tasks ek core se doosre core par ping-pong ki tarah ghoomte rahenge (thrashing). Humne isse rokne ke liye 3 safeguards lagaye hain:
1. **Queue Tail Extraction**: Donor ke ready queue ke **tail** se task nikala jata hai. Jo task head par run hone wala tha, uski cache locality disturb nahi hoti.
2. **`max_migrations_per_task <= 1`**: Ek task maximum 1 baar migrate ho sakta hai. Dobara usse migrate nahi kiya ja sakta.
3. **Immediate Work Ingestion**: Jab idle recipient task receive karta hai, woh usse turant running task mark kar leta hai taaki agle tick par woh khud donor na ban jaye!

---

### 4.3 CPUCore Migration Support ([`core/core.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/core.py))

`CPUCore` class ko Phase 2 ke liye upgrade kiya gaya hai:
- `migrations_in`: Kitne tasks is core par bahar se aaye.
- `migrations_out`: Kitne tasks is core ne dusre cores ko donate kiye.
- `migration_overhead_ticks`: Migration ke karan kitna context-switch time kharch hua.
- `migration_penalty_remaining`: Jab core naya migrated task receive karta hai, toh next clock tick par execution pause karke migration overhead lagta hai (representing cache invalidation / TLB flush).

---

### 4.4 Metrics Engine Comparison ([`core/metrics.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/metrics.py))

`MetricsEngine.compare_static_vs_dynamic(static_m, dynamic_m)` dono phases ka mathematical diff nikalta hai:
- **Makespan Reduction %**: $\frac{\text{Makespan}_{static} - \text{Makespan}_{dyn}}{\text{Makespan}_{static}} \times 100\%$
- **Speedup Gain**: $\text{Speedup}_{dyn} - \text{Speedup}_{static}$
- **Fairness Gain**: $J_{dyn} - J_{static}$
- **Tail Latency Reduction %**: $\frac{P95_{static} - P95_{dyn}}{P95_{static}} \times 100\%$

---

## 5. The Step-by-Step Life of a Migrated Task

Samajhne ke liye, aaiye ek specific task **Task #12** ka timeline trace dekhte hain:

```
Workload Setup:
- Task #12 arrives at Clock Tick 12 with Burst Time = 36 cycles.
- Round-Robin assigns Task #12 to Core 0 (since 12 % 4 == 0).
```

### Scenario A: In Phase 1 (Static Round-Robin)
1. **Tick 12**: Task #12 Core 0 ke ready queue mein enter hota hai.
2. **The Problem**: Core 0 par pehle se Task #0 (running, burst 36), Task #4 (queued, burst 36), aur Task #8 (queued, burst 36) lage hue hain!
3. **Queue Wait**:
   - Task #0 finishes at Tick 36.
   - Task #4 finishes at Tick 72.
   - Task #8 finishes at Tick 108.
4. **Tick 108**: Task #12 finally starts execution (**Waiting Time = 96 ticks!**).
5. **Tick 144**: Task #12 finishes.
   - In the meantime, **Cores 1, 2, and 3 were sitting completely IDLE** since tick 20!

---

### Scenario B: In Phase 2 (Dynamic Predictive Balancing)
1. **Tick 12**: Task #12 Core 0 ke ready queue mein enter hota hai.
2. **Tick 14**: 
   - Core 1, 2, 3 apne chote tasks finish karke idle ho jaate hain ($W_1 = 0, W_2 = 0, W_3 = 0$).
   - `CoreLoadPredictor` checks disparity:
     $$\hat{L}_{Core0} \approx 100\text{ cycles}, \quad \hat{L}_{Core1} = 0\text{ cycles} \implies \text{Disparity} = 100 \gg 15.0$$
3. **Tick 15 (Migration Triggered!)**:
   - Migration Controller activates: Core 0 ke queue tail se **Task #12 extract** hota hai.
   - Task #12 is transferred to **Core 1**.
   - Core 1 charges **1 tick migration penalty** (Tick 15 is spent on context switch/cache prep).
4. **Tick 16**: Task #12 starts running on Core 1 (**Waiting Time = only 4 ticks!**).
5. **Tick 52**: Task #12 finishes completely!
6. **Comparison for Task #12**:
   - Completion Time in Phase 1: **Tick 144**
   - Completion Time in Phase 2: **Tick 52** (Almost 3x faster!)

---

## 6. Real-World Analogies

### Analogy 1: Bank Manager with Token Queues
- **Phase 1 (Static)**:
  - Security guard assigns tokens: Counter 0 gets clients with 50-page audits.
  - Counter 0 clerk is sweating and overwhelmed.
  - Counters 1, 2, and 3 are empty and clerks are drinking tea.
  - Security guard refuses to let anyone switch lines because *"Rules are rules (Static)"*.
- **Phase 2 (Dynamic Predictive)**:
  - Smart Branch Manager stands in the hall.
  - He looks at Counter 0's long line and announces: *"Customers at the back of Counter 0, please come over to Counter 1 and 2!"*
  - Everyone gets served simultaneously; bank closes 3 hours earlier!

---

### Analogy 2: Highway Toll Booth & FastTag
- **Phase 1 (Static)**:
  - 4 Toll Booths on a highway. GPS strictly maps lanes: Lane 0 for Car 0, 4, 8, 12...
  - If heavy 18-wheeler trucks arrive on Lane 0, Lane 0 backs up for 2 kilometers.
  - Lanes 1, 2, and 3 are empty, but barriers prevent cars from switching lanes.
- **Phase 2 (Dynamic)**:
  - Smart electronic signs detect the jam 500 meters ahead.
  - Electronic barriers open, smoothly funneling trailing cars into Lanes 1, 2, and 3 before a traffic jam can form.

---

## 7. How Real-World Operating Systems Do This

Yeh project sirf theory nahi hai — yeh modern OS kernels ke core architecture par based hai:

### 1. Linux Kernel (CFS - Completely Fair Scheduler):
- Linux har CPU core ke liye ek runqueue (`rq`) maintain karta hai.
- **Scheduling Domains (`sched_domain`)**: Linux cores ko hierarchical domains (SMT, Multi-Core, NUMA) mein divide karta hai.
- **`load_balance()` function**:
  - Jab koi CPU idle hota hai, kernel `load_balance()` call karta hai.
  - Overloaded core (`busiest_rq`) se tasks ko pull karta hai (**Work Stealing**).
- **Migration Cost (`migration_cost_ns`)**:
  - Linux track karta hai ki task kitne samay pehle chala tha. Agar task abhi-abhi chala hai, toh uski cache hot hoti hai, isliye kernel usse migrate karne se bachta hai jab tak ki imbalance bohot zyada na ho (exact match to our `extract_task_for_migration()` from queue tail!).

### 2. Windows NT Kernel:
- Windows har thread ke liye ek **Ideal Processor** assign karta hai.
- Dispatcher periodic load balancer run karta hai jo ready queues ko rebalance karta hai aur dynamic affinity migration allow karta hai.

---

## 8. Mathematical Formulas & Step-by-Step Numerical Walkthrough

Hamare benchmark runs ([`experiments/phase2_comparison_results.json`](file:///c:/Users/parth/OneDrive/Documents/OS_2/experiments/phase2_comparison_results.json)) ke actual numbers ka proof:

### 1. Makespan Reduction:
$$\text{Makespan}_{static} = 724\text{ ticks}, \quad \text{Makespan}_{dynamic} = 300\text{ ticks}$$
$$\text{Reduction} = \frac{724 - 300}{724} \times 100\% = \mathbf{58.56\% \approx 58.6\%}$$
*(Poore multi-core system ka total execution time adhe se bhi zyada kam ho gaya!)*

---

### 2. Speedup Boost (4 Cores):
$$\text{Single Core Baseline Makespan} = 1082\text{ ticks}$$
- **Phase 1 Static Speedup**:
  $$S_{static} = \frac{1082}{724} = \mathbf{1.49x} \quad (\text{Efficiency} = 37.3\%)$$
- **Phase 2 Dynamic Speedup**:
  $$S_{dynamic} = \frac{1082}{300} = \mathbf{3.60x} \quad (\text{Efficiency} = \mathbf{90.1\%})$$
- **Speedup Gain**:
  $$\Delta S = 3.60x - 1.49x = \mathbf{+2.11x}$$
  *(Hardware efficiency 37.3% se badhkar 90.1% ho gayi!)*

---

### 3. Load Imbalance Standard Deviation ($\sigma$):
- **Phase 1 Static**:
  $$B_{static} = [721, 117, 112, 128], \quad \bar{B} = 269.5$$
  $$\sigma_{static} = \mathbf{260.7\text{ ticks}}$$
- **Phase 2 Dynamic**:
  $$B_{dynamic} = [283, 297, 285, 280], \quad \bar{B} = 286.25$$
  $$\sigma_{dynamic} = \sqrt{\frac{(283-286.25)^2 + (297-286.25)^2 + (285-286.25)^2 + (280-286.25)^2}{4}} = \mathbf{6.5\text{ ticks}}$$
- **Imbalance Reduction**:
  $$\frac{260.7 - 6.5}{260.7} \times 100 = \mathbf{97.5\% \text{ reduction in load imbalance!}}$$

---

### 4. Jain's Fairness Index ($J$):
- **Phase 1 Static**: $J_{static} = \mathbf{0.516}$ (Extreme unfairness, Core 0 bottleneck).
- **Phase 2 Dynamic**:
  $$\sum B_i = 1145, \quad \left(\sum B_i\right)^2 = 1,311,025$$
  $$\sum B_i^2 = 283^2 + 297^2 + 285^2 + 280^2 = 80,089 + 88,209 + 81,225 + 78,400 = 327,923$$
  $$J_{dynamic} = \frac{1,311,025}{4 \times 327,923} = \frac{1,311,025}{1,311,692} = \mathbf{0.9995 \approx 1.000}$$
- **Fairness Restored**: $J$ jumped from **0.516 $\to$ 1.000** (Mathematically perfect balance!).

---

### 5. P95 Response Tail Latency:
- **Phase 1 Static**: 95% tasks took up to **461.0 ticks** to start executing.
- **Phase 2 Dynamic**: 95% tasks started executing within **155.0 ticks**.
- **Latency Improvement**: **-66.4% tail latency reduction!**

---

## 9. Benchmark Comparison Table (Phase 1 vs. Phase 2)

| Evaluation Metric | Phase 1 (Static Baseline) | Phase 2 (Dynamic Predictive) | Improvement / Delta |
| :--- | :---: | :---: | :---: |
| **Makespan (Total Ticks)** | 724 ticks | **300 ticks** | **-58.6% execution time** |
| **Speedup (vs 1-Core)** | 1.49x | **3.60x** | **+2.11x speedup boost** |
| **Multi-Core Efficiency (%)** | 37.3% | **90.1%** | **+52.8% hardware utilization** |
| **Load Imbalance ($\sigma$)** | 260.7 ticks | **6.5 ticks** | **-97.5% load variance** |
| **Jain's Fairness Index** | 0.516 | **1.000** | **+0.483 (Perfect Fairness)** |
| **P95 Response Latency** | 461.0 ticks | **155.0 ticks** | **-66.4% latency drop** |
| **Average CPU Utilization** | 37.2% | **95.4%** | **+58.2% active work** |
| **Core 0 Busy Ticks** | 721 ticks (99.6%) | **283 ticks (94.3%)** | Bottleneck eliminated |
| **Cores 1–3 Idle Ticks** | ~605 ticks idle each | **<20 ticks idle each** | Wasted cycles eliminated |
| **Dynamic Task Migrations** | 0 (Static) | **67 tasks migrated** | Total overhead: 67 ticks |

---

## 10. Viva / Interview Master Questions & Answers

Agar exam ya interview mein examiner project ke baare mein pooche, toh yeh answers perfect hain:

### Q1: "Aapne ready queue ke TAIL se task kyun nikala, HEAD se kyun nahi?"
> **Answer**: Ready queue ke head par jo task hota hai, ho sakta hai CPU usse agle hi tick par pick karne wala ho, ya uske data cache lines pehle se warm ho rahe hon. Agar hum tail se task uthate hain, toh hum active execution stream ko interrupt nahi karte aur **Cache Locality** preserve rehti hai.

---

### Q2: "Migration Thrashing (Ping-Pong Effect) kya hota hai aur aapne isse kaise roka?"
> **Answer**: Agar hum threshold set na karein, toh Core A se task Core B par jayega, agle tick par Core B thoda heavy ho jayega toh wapas Core A par bhej dega! Is live-lock ko **Thrashing** kehte hain.
> Humne 3 safeguards lagaye:
> 1. `max_migrations_per_task = 1` (Ek task sirf 1 baar migrate ho sakta hai).
> 2. `Disparity >= Threshold (15 cycles)` (Chote-mote difference par migration trigger nahi hota).
> 3. Task extract karne se pehle verify kiya jata hai ki donation ke baad donor khud recipient se kam loaded na ho jaye.

---

### Q3: "Migration Penalty include karna kyun zaroori hai?"
> **Answer**: Real hardware mein jab koi thread ek core se dusre core par jata hai, toh L1/L2 cache invalidation hota hai, TLB flush hota hai, aur OS context switch overhead lagta hai. Agar hum migration penalty model na karein, toh simulation unrealistic ho jayega. Humne realistic 1 tick context penalty model kiya hai.

---

### Q4: "Jain's Fairness Index kya represent karta hai?"
> **Answer**: Jain's Fairness Index ($J = \frac{(\sum B_i)^2}{M \sum B_i^2}$) multi-core system mein workload distribution ki equality measure karta hai. Iski value $1/M$ se lekar $1.0$ ke beech hoti hai:
> - $J = 1.0$: Sabhi cores ne barabar cycles execute kiye (perfect balance).
> - $J < 0.7$: System mein severe bottleneck hai (jaise Phase 1 mein $J=0.516$).

---

### Q5: "Makespan aur Response Time mein kya antar hai?"
> **Answer**: 
> - **Makespan**: Poora batch of tasks complete hone mein laga total time (system throughput perspective).
> - **Response Time**: Ek individual task aane ke kitne samay baad pehli baar execute hona shuru hua ($T_{start} - T_{arrival}$) (user experience perspective).

---

## 11. Web Dashboard Visualizer Guide

Website (`http://127.0.0.1:5000`) par interactive features:
1. **Scheduler Engine Dropdown**:
   - `Phase 2: Predictive Dynamic Balancing (AI/Heuristic)`
   - `Phase 1: Static Distribution (Baseline No Migration)`
2. **Migration Penalty Selector**: Test 0 ticks (ideal), 1 tick (realistic cache penalty), 2 ticks (heavy context switch).
3. **Interactive Gantt Chart**:
   - 🔴 **Red Blocks**: Heavy burst tasks.
   - 🔵 **Blue Blocks**: Light burst tasks.
   - 🟣 **Purple Glowing Blocks (`T#*`)**: Migrated tasks (moved from overloaded core).
   - 🟡 **Amber Striped Blocks (`mig`)**: Cache invalidation penalty cycles.
4. **Click-to-Inspect Task**: Gantt chart par kisi bhi task par click karke uski puri history dekh sakte hain!

---

## 12. How to Run, Test, and Verify Phase 2

### 1. Run Phase 2 CLI Comparison Benchmark:
```bash
python run_phase2.py
```

### 2. Run Automated Unit Tests:
```bash
python -m pytest tests/
```

### 3. Launch the Web Dashboard:
```bash
python web/server.py
```
Open **`http://127.0.0.1:5000`** in your browser. Click **Phase 2 (Dynamic Rebalance)** to see the live rebalancing in action!
