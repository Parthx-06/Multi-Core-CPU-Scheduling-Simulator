# Phase 1: Complete In-Depth Guide & Analysis (Multi-Core CPU Scheduling)
### (Hinglish + English Comprehensive Documentation)

---

## 📑 Table of Contents
1. [Project Overview & Phase 1 Objective (परिचय)](#1-project-overview--phase-1-objective)
2. [Complete System Architecture & Inter-relations (सिस्टम कैसे आपस में जुड़ा है)](#2-complete-system-architecture--inter-relations)
3. [Deep-Dive into Backend Core Components](#3-deep-dive-into-backend-core-components)
   - [3.1 Task Model (`core/task.py`)](#31-task-model-coretaskpy)
   - [3.2 CPU Core Model (`core/core.py`)](#32-cpu-core-model-corecorepy)
   - [3.3 Static Scheduler (`core/scheduler.py`)](#33-static-scheduler-coreschedulerpy)
   - [3.4 Workload Generator (`core/workload.py`)](#34-workload-generator-coreworkloadpy)
   - [3.5 Metrics Engine (`core/metrics.py`)](#35-metrics-engine-coremetricspy)
4. [Web Dashboard Architecture & UI Components (`web/`)](#4-web-dashboard-architecture--ui-components)
5. [In-Depth Analysis with Real-Life Examples (आसान उदाहरणों के साथ)](#5-in-depth-analysis-with-real-life-examples)
6. [Mathematical Formulas & Step-by-Step Numerical Walkthrough](#6-mathematical-formulas--step-by-step-numerical-walkthrough)
7. [Benchmark Comparison Table (Balanced vs Skewed)](#7-benchmark-comparison-table)
8. [Why Static Fails & How Phase 2 Solves It (Phase 2 का रास्ता)](#8-why-static-fails--how-phase-2-solves-it)
9. [How to Run & Verify the Project](#9-how-to-run--verify-the-project)

---

## 1. Project Overview & Phase 1 Objective

### English:
This project, **"Load-Balanced CPU Scheduling for Multi-Core Systems"**, studies how multi-core processors allocate and execute computational workloads. 
- **Phase 1 (Baseline)**: Implements **Static Task Distribution**, where tasks are permanently assigned to cores upon arrival. There is **no task migration**. We study its performance under **balanced** and **skewed (uneven)** workloads.
- **Phase 2 (Proposed Improvement)**: Will implement dynamic load balancing using AI/heuristic load prediction and work stealing/migration.

### Hinglish (सरल भाषा में):
Yeh project yeh samajhne ke liye banaya gaya hai ki multi-core CPUs (jaise Quad-Core ya Octa-Core processors) mein jab tasks aate hain, toh unko cores ke beech kaise baanta jata hai.
- **Phase 1 ka main kaam**: Ek baseline (starting point) banana jahan hum **Static Task Distribution** use karte hain. "Static" ka matlab hai ki ek baar jo task jis core ko mil gaya, woh wahi execute hoga — chahe woh core thak jaye aur baaki cores aaram se khali baithe rahein! (No migration).
- Is phase mein hum proof karte hain ki jab workload uneven ya skewed hota hai, toh Static Scheduling kaise fail ho jata hai aur hume **Phase 2 (Dynamic Load Balancing / AI prediction)** ki zaroorat kyun padti hai.

---

## 2. Complete System Architecture & Inter-relations

Neeche diye gaye flowchart mein dekhiye ki system ke saare components ek doosre se kaise baat karte hain:

```
+-----------------------------------------------------------------------------------+
|                                  USER / BROWSER                                   |
|   Controls (Select Cores, Workload, Policy)  <--->  Visual Dashboard (Gantt, Charts)|
+------------------------------------------+----------------------------------------+
                                           | HTTP Requests (REST API)
                                           v
+-----------------------------------------------------------------------------------+
|                             FLASK WEB SERVER (`web/server.py`)                    |
|   - GET  /api/benchmarks  --> Reads precomputed benchmarks from disk             |
|   - POST /api/simulate    --> Triggers simulation with user parameters            |
+------------------------------------------+----------------------------------------+
                                           | Calls Python Engine
                                           v
+-----------------------------------------------------------------------------------+
|                        WORKLOAD GENERATOR (`core/workload.py`)                    |
|   - Generates list of Task objects:                                               |
|     * Balanced (Uniform burst times)                                             |
|     * Skewed Hotspot (Every 4th task has 6x burst)                                |
|     * Skewed Bimodal (80% light tasks + 20% heavy elephant tasks)                 |
+------------------------------------------+----------------------------------------+
                                           | Passes Tasks to Scheduler
                                           v
+-----------------------------------------------------------------------------------+
|                         STATIC SCHEDULER (`core/scheduler.py`)                    |
|   - Master discrete clock (Tick 0, 1, 2, ... Makespan)                            |
|   - Assigns arriving tasks using: Round-Robin / Arrival-Greedy / Random           |
|   - Coordinates M CPU Cores                                                       |
+---------------------+--------------------+-------------------+--------------------+
                      |                    |                   |
                      v                    v                   v
                +-------------+      +-------------+     +-------------+
                | CPU Core 0  |      | CPU Core 1  | ... | CPU Core M  |
                | (`core.py`) |      | (`core.py`) |     | (`core.py`) |
                | Local Queue |      | Local Queue |     | Local Queue |
                | Busy/Idle   |      | Busy/Idle   |     | Busy/Idle   |
                +------+------+      +------+------+     +------+------+
                       |                    |                   |
                       +--------------------+-------------------+
                                           | Execution Trace & Finished Tasks
                                           v
+-----------------------------------------------------------------------------------+
|                         METRICS ENGINE (`core/metrics.py`)                        |
|   Computes: Makespan, Speedup, Efficiency, Load Imbalance (StdDev & Jain's),      |
|             Throughput, Avg/P95 Response Time, CPU Utilization %                  |
+------------------------------------------+----------------------------------------+
                                           | Returns JSON Output
                                           v
+-----------------------------------------------------------------------------------+
|                           FRONTEND RENDERER (`web/app.js`)                        |
|   - Updates 5 KPI Metric Cards                                                    |
|   - Draws Gantt Timeline (Blocks showing task execution & idle gaps)             |
|   - Renders Chart.js (Core load bars + Queue length curves over time)             |
+-----------------------------------------------------------------------------------+
```

---

## 3. Deep-Dive into Backend Core Components

### 3.1 Task Model ([`core/task.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/task.py))
Har computational unit ko ek **`Task`** object represent karta hai.

```python
@dataclass
class Task:
    task_id: int              # Unique identifier (T1, T2, ...)
    arrival_time: int         # Kis clock tick par task aaya
    burst_time: int           # Kitne execution cycles chahiye
    remaining_time: int       # Kitna kaam bacha hai
    state: TaskState          # PENDING -> READY -> RUNNING -> COMPLETED
    assigned_core_id: int     # Kis CPU core ko statically assign hua
    start_time: int           # Core ne pehli baar kab run karna shuru kiya
    completion_time: int      # Task kab 100% khatam hua
    tag: str                  # "heavy", "light", "normal"
```

#### Task Lifecycle (State Transitions):
1. **`PENDING`**: Task abhi CPU system mein enter nahi hua hai (`tick < arrival_time`).
2. **`READY`**: Task system mein aa gaya aur kisi core ke **Ready Queue** mein khada hai.
3. **`RUNNING`**: Core task ko pick karke apna computational tick use kar raha hai (`remaining_time -= 1`).
4. **`COMPLETED`**: Jab `remaining_time == 0` ho jata hai, tab task finish mark hota hai.

---

### 3.2 CPU Core Model ([`core/core.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/core.py))
Har CPU Core ek independent hardware processor execution unit ki tarah behave karta hai.

- **Local FIFO Queue (`ready_queue`)**: Is core ko assign kiye gaye tasks yahan queue mein wait karte hain.
- **Cycle-by-Cycle Execution (`step(current_tick)`)**:
  - Agar core ke paas koi running task nahi hai aur queue mein task hai $\to$ queue se task nikaalo aur run karo.
  - Agar task run ho raha hai $\to$ uska `remaining_time` 1 kam karo aur `total_busy_ticks += 1`.
  - Agar core ke paas koi kaam nahi hai $\to$ `total_idle_ticks += 1` (wasted cycles).
- **Timeline Logger**: Har tick ka snapshot store karta hai:
  `{"tick": 14, "task_id": 3, "state": "BUSY", "queue_len": 4}`. Yeh timeline aage chalkar Gantt chart banane ke kaam aati hai.

---

### 3.3 Static Scheduler ([`core/scheduler.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/scheduler.py))
Yeh master coordinator hai jo discrete clock ko aage badhata hai aur static distribution logic implement karta hai:

#### Static Distribution Policies:
1. **`Round-Robin Static`**:
   - Formula: $\text{Core} = \text{Task Index} \pmod M$
   - Example (4 cores): Task 0 $\to$ Core 0, Task 1 $\to$ Core 1, Task 2 $\to$ Core 2, Task 3 $\to$ Core 3, Task 4 $\to$ Core 0...
   - *Problem*: Isse task ke size ka koi andaza nahi hota. Agar bade tasks Core 0 par aa gaye, toh Core 0 phans jata hai.
2. **`Arrival-Time Greedy (Min-Pending at Arrival)`**:
   - Task aate waqt dekhta hai ki kis core ke paas sabse kam total pending work hai.
   - Us core ko task de diya jata hai.
   - *Notice*: Yeh static hai kyunki assignment ke baad **strictly no migration** hota hai.
3. **`Random Static`**:
   - Randomly kisi bhi core ko de deta hai.

---

### 3.4 Workload Generator ([`core/workload.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/workload.py))
Multi-core systems ki testing ke liye hum teen tarah ke workloads generate karte hain:

1. **Balanced Workload**:
   - Sabhi tasks ke burst times kareeb-kareeb ek jaise hote hain ($\mu = 12, \sigma = 3$).
   - Arrivals regular gap par hote hain.
2. **Skewed Hotspot Workload**:
   - Janbujhkar har 4th task ko **6x bada burst time (36 cycles)** diya jata hai.
   - Round-Robin policy mein yeh saare heavy tasks seedhe **Core 0** par chale jaate hain.
   - Result: Core 0 over-burdened ho jata hai aur Core 1, 2, 3 khali baithe rehte hain.
3. **Skewed Bimodal Workload (Elephant & Mouse)**:
   - Real-world cloud/OS workload jahan 80% tasks chote hote hain (3 to 6 ticks) aur 20% tasks bohot lambe hote hain (35 to 60 ticks).
   - Tasks clumps mein aate hain, jisse queue backup create hota hai.

---

### 3.5 Metrics Engine ([`core/metrics.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/metrics.py))
Simulation khatam hone ke baad, yeh engine pure run ka mathematical analysis karta hai:
- **Makespan**: Sabhi tasks ko complete karne mein laga total time.
- **Speedup**: $\frac{\text{Makespan (1 Core)}}{\text{Makespan (M Cores)}}$
- **Efficiency**: $\frac{\text{Speedup}}{M} \times 100\%$
- **Load Imbalance (StdDev)**: Cores ke busy time ka standard deviation $\sigma$.
- **Jain's Fairness Index**: $J = \frac{(\sum B_i)^2}{M \sum B_i^2}$. (1.0 = perfect fairness).
- **Avg & P95 Response Time**: Task aane se lekar uske pehle execution tak ka waiting time.
- **CPU Utilization**: Har core kitne percent time busy raha aur kitne percent idle.

---

## 4. Web Dashboard Architecture & UI Components

Website ko responsive, visual aur real-time experience dene ke liye banaya gaya hai.

### Files & Unka Kaam:
1. **[`web/server.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/server.py) (Flask Backend Server)**:
   - Local port `5000` par run karta hai.
   - `/api/benchmarks` endpoint: Pre-calculated benchmarks return karta hai.
   - `/api/simulate` endpoint: Jab user UI mein sliders ya dropdown change karke "Run Simulation" dabata hai, yeh endpoint turant simulation engine ko run karta hai aur timeline traces + metrics JSON mein return karta hai.
2. **[`web/index.html`](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/index.html) (Frontend Structure)**:
   - **Control Panel**: Workload selector, CPU Cores dropdown (2, 4, 8), Policy dropdown, Task count slider.
   - **5 Key KPI Cards**: Load Imbalance, Speedup, Makespan, Response Time, CPU Utilization.
   - **Gantt Chart Viewport**: Discrete timeline viewer.
   - **Visual Charts Area**: Canvas elements for Chart.js.
   - **Benchmark Comparison Table**: Full comparative table.
3. **[`web/style.css`](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/style.css) (Modern Aesthetics)**:
   - Dark mode background (`#0b0f19`) with glassmorphism blur panels (`backdrop-filter: blur(16px)`).
   - Curated accents: Cyan (`#06b6d4`), Emerald Green (`#10b981`), Amber (`#f59e0b`), Red (`#ef4444`).
   - Typography: Google Fonts *Inter* for crisp UI text and *JetBrains Mono* for technical metrics and numbers.
4. **[`web/app.js`](file:///c:/Users/parth/OneDrive/Documents/OS_2/web/app.js) (Frontend Logic & Interactivity)**:
   - **Gantt Chart Renderer**: Consecutive ticks of the same task ko merge karke proportional width horizontal blocks banata hai. Heavy tasks ko red aur light tasks ko blue color deta hai. Idle gaps clearly dikhte hain.
   - **Chart.js Bar Chart**: Har core ke Busy vs Idle cycles ka stacked bar chart dikhata hai.
   - **Chart.js Line Chart**: Simulation ticks ke dauran har core ki queue length kaise upar-neeche hui, uska live curve plot karta hai.

---

## 5. In-Depth Analysis with Real-Life Examples

Ek practical real-world analogy se samajhte hain ki Balanced aur Skewed workload mein kya hota hai:

### Analogy: Bank Counter System (4 Cash Counters)

Maan lijiye ek bank mein 4 Cash Counters (Core 0, Core 1, Core 2, Core 3) hain:

```
[Customer Queue Entry]
         |
         v
+------------------+
| Security Guard   | ---> Round-Robin static rule: 
| (Static Dispatch)|      Token 1 -> Counter 0, Token 2 -> Counter 1,
+------------------+      Token 3 -> Counter 2, Token 4 -> Counter 3...
```

---

### Scenario A: Balanced Workload (Sabhi Customers Normal Hain)
- Har customer ke paas chota kaam hai (paise jama karna, 2 se 3 minute).
- **Result**:
  - Counter 0, 1, 2, aur 3 sabhi lagbhag barabar time busy rehte hain.
  - Sabhi counters par line barabar chalti hai.
  - **Makespan = 242 ticks**.
  - **Speedup = 3.88x** (4 counters milkar lagbhag 4 guna tezi se kaam nipta dete hain).
  - **Fairness Index = 1.000** (Sabhi counters par equal load).

---

### Scenario B: Skewed Hotspot Workload (The Disaster of Static Scheduling)
- Ab maan lijiye **har 4th customer ek bada business client hai**, jisko 50 company accounts ka lengthy audit aur payment verification karwana hai (takes 36 minutes instead of 6 minutes).
- Security guard ka **Static Rule** abhi bhi wahi hai: Token 0 $\to$ Counter 0, Token 4 $\to$ Counter 0, Token 8 $\to$ Counter 0!
- **Kya hota hai?**:
  - Saare massive heavy clients **Counter 0** par jaakar khade ho jaate hain.
  - Counter 0 par lamba traffic jam lag jata hai (Core 0 is 99.6% busy for 721 ticks!).
  - Counter 1, 2, aur 3 apne chote-chote customers ko jaldi free karke **khali baithe rehte hain (over 80% idle time)!**
  - Static rule ki wajah se Counter 0 ka koi bhi customer Counter 1 ya 2 par nahi jaa sakta (No task migration).
  - **Makespan jumps to 724 ticks** (poora bank 3 guna late close hota hai).
  - **Speedup collapses to 1.49x** (4 counters hone ke bawajood kaam lagbhag 1 counter ki speed par ho raha hai!).
  - **Efficiency drops to 37.3%**.

---

## 6. Mathematical Formulas & Step-by-Step Numerical Walkthrough

Neeche diye gaye calculations wahi hain jo [`core/metrics.py`](file:///c:/Users/parth/OneDrive/Documents/OS_2/core/metrics.py) code ke andar execute karta hai:

### 1. Speedup ($S$)
$$\text{Speedup} = \frac{\text{Makespan}(1\text{ Core Baseline})}{\text{Makespan}(M\text{ Cores})}$$
- **Balanced Workload (4 Cores)**:
  $$\text{Makespan}_{1\text{ core}} = 940, \quad \text{Makespan}_{4\text{ cores}} = 242$$
  $$S = \frac{940}{242} = \mathbf{3.88x}$$
- **Skewed Hotspot Workload (4 Cores Round-Robin)**:
  $$\text{Makespan}_{1\text{ core}} = 1082, \quad \text{Makespan}_{4\text{ cores}} = 724$$
  $$S = \frac{1082}{724} = \mathbf{1.49x} \quad \text{(Catastrophic drop!)}$$

---

### 2. Efficiency ($E$)
$$\text{Efficiency} = \left(\frac{\text{Speedup}}{M}\right) \times 100\%$$
- **Balanced (4 Cores)**: $\frac{3.88}{4} \times 100 = \mathbf{97.1\%}$ (Excellent hardware utilization).
- **Skewed Hotspot (4 Cores)**: $\frac{1.49}{4} \times 100 = \mathbf{37.3\%}$ (62.7% multi-core capacity wasted).

---

### 3. Load Imbalance Standard Deviation ($\sigma$)
Har core ke busy ticks ka average $\bar{B} = \frac{1}{M}\sum_{i=0}^{M-1} B_i$:
$$\sigma = \sqrt{\frac{1}{M}\sum_{i=0}^{M-1}(B_i - \bar{B})^2}$$
- **Balanced (4 Cores)**:
  $$B = [238, 234, 237, 228], \quad \bar{B} = 234.25$$
  $$\sigma = \sqrt{\frac{(238-234.25)^2 + (234-234.25)^2 + (237-234.25)^2 + (228-234.25)^2}{4}} = \mathbf{3.9\text{ ticks}}$$
- **Skewed Hotspot (4 Cores Round-Robin)**:
  $$B = [721, 117, 112, 128], \quad \bar{B} = 269.5$$
  $$\sigma = \sqrt{\frac{(721-269.5)^2 + (117-269.5)^2 + (112-269.5)^2 + (128-269.5)^2}{4}} = \mathbf{260.7\text{ ticks}}$$
  *(Loads mein 260+ ticks ka bhari antar hai!)*

---

### 4. Jain's Fairness Index ($J$)
$$J(B_0, B_1, \dots, B_{M-1}) = \frac{\left(\sum_{i=0}^{M-1} B_i\right)^2}{M \times \sum_{i=0}^{M-1} B_i^2}$$
- Agar sabhi cores par equal load hai, toh $J = 1.0$.
- Agar ek core saara kaam kare aur baaki khali rahein, toh $J \to \frac{1}{M} = \frac{1}{4} = 0.25$.
- **Balanced Workload**: $J = \mathbf{1.000}$ (Near perfect fairness).
- **Skewed Hotspot Workload**:
  $$\sum B_i = 1078, \quad \left(\sum B_i\right)^2 = 1,162,084$$
  $$\sum B_i^2 = 721^2 + 117^2 + 112^2 + 128^2 = 519,841 + 13,689 + 12,544 + 16,384 = 562,458$$
  $$J = \frac{1,162,084}{4 \times 562,458} = \frac{1,162,084}{2,249,832} = \mathbf{0.516}$$
  *(Jain's index 1.0 se girkar 0.516 ho gaya, which proves high unfairness).*

---

### 5. Task Latencies (Response, Turnaround & Waiting Times)
- **Response Time ($R$)**: $R = \text{start\_time} - \text{arrival\_time}$
  - *Balanced*: P95 Response Time = **70.0 ticks**
  - *Skewed Hotspot*: P95 Response Time = **461.0 ticks** (**6.5x latency explosion** because tasks are stuck behind the heavy elephant in Core 0's queue).

---

## 7. Benchmark Comparison Table

Yeh real data hamare baseline benchmark run [`experiments/phase1_benchmark_results.json`](file:///c:/Users/parth/OneDrive/Documents/OS_2/experiments/phase1_benchmark_results.json) se nikala gaya hai:

| Workload | Cores | Policy | Makespan | Speedup | Efficiency | Load Imbalance (StdDev) | Jain's Index | P95 Response Time | Avg CPU Util |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Balanced** | 2 | Round-Robin | 478 | 1.97x | 98.3% | 6.5 | 1.000 | 287.0 t | 98.5% |
| **Balanced** | 4 | Round-Robin | **242** | **3.88x** | **97.1%** | **3.9** | **1.000** | **70.0 t** | **96.8%** |
| **Balanced** | 8 | Round-Robin | 175 | 5.37x | 67.1% | 2.7 | 1.000 | 2.0 t | 66.8% |
| **Skewed Hotspot** | 2 | Round-Robin | 836 | 1.29x | 64.7% | 294.0 | 0.771 | 610.0 t | 64.7% |
| **Skewed Hotspot** | 4 | Round-Robin | **724** | **1.49x** | **37.3%** | **260.7** | **0.516** | **461.0 t** | **37.2%** |
| **Skewed Hotspot** | 4 | Arrival Greedy | 286 | 3.78x | 94.5% | 9.9 | 0.999 | 97.0 t | 94.1% |
| **Skewed Hotspot** | 8 | Round-Robin | 373 | 2.90x | 36.2% | 130.4 | 0.516 | 165.0 t | 36.2% |
| **Skewed Bimodal** | 4 | Round-Robin | 461 | 2.99x | 74.8% | 75.6 | 0.954 | 254.0 t | 74.7% |
| **Skewed Bimodal** | 4 | Arrival Greedy | 370 | 3.73x | 93.2% | 15.2 | 0.998 | 183.0 t | 93.2% |

---

## 8. Why Static Fails & How Phase 2 Solves It

### Static Scheduling ki Kamzori (The Fundamental Flaw):
1. **Blind Allocation**: Static distribution (jaise Round-Robin) task assign karte waqt yeh nahi jaanta ki aane wala task 2 second lega ya 2 ghante.
2. **No Dynamic Correction (No Migration)**: Agar ek baar galat assignment ho gaya, toh task us core par bandh jata hai. Dusre cores jab apna kaam jaldi khatam kar lete hain, tab bhi woh idle baith kar tamasha dekhte hain par overburdened core ki madad nahi kar sakte.
3. **Arrival Greedy ki Limitations**: Halanki Arrival Greedy thoda behtar karta hai, par agar execution ke beech mein achanak burst pattern badal jaye ya execution rates fluctuate karein, toh yeh bhi phans jata hai.

---

### Phase 2: What We Will Build Next (Proposed Improvement):
Phase 2 mein hum **Dynamic Load Balancing with Predictive AI / Adaptive Heuristics** banayenge:
1. **Load Prediction Engine**:
   - Har core ke recent queue lengths aur execution rates ko continuously monitor karega.
   - Future core load ($L_{future}$) ko predict karega:
     $$\hat{L}_{core}(t + \Delta t) = \alpha \cdot \text{QueueLength}(t) + (1-\alpha) \cdot \text{RecentExecutionRate}$$
2. **Dynamic Work Stealing / Task Migration**:
   - Jab koi core idle hone lage ya severe imbalance detect ho ($\text{Load}_{max} - \text{Load}_{min} > \text{Threshold}$):
   - Overloaded core ki queue se tasks ko automatically less-loaded / idle cores par **migrate** kiya jayega!
3. **Imbalance Elimination**:
   - Skewed workload ka Makespan 724 ticks se ghat kar 250-280 ticks ke kareeb aayega, speedup wapas 3.7x+ ho jayega, aur idle cycles eliminate ho jayenge!

---

## 9. How to Run & Verify the Project

### 1. Run CLI Benchmark:
Terminal mein run karein:
```bash
python run_phase1.py
```
Isse terminal par colorful tables display hongi jo Balanced aur Skewed workloads ke numbers dikhayengi.

### 2. Run Automated Unit Tests:
```bash
python -m pytest tests/
```
Saare 6 unit tests pass honge: Task lifecycle, CPU core stepping, Static Round-Robin distribution, aur Metrics calculations.

### 3. Open Interactive Web Dashboard:
Make sure Flask server is running:
```bash
python web/server.py
```
Apne browser mein open karein: **`http://127.0.0.1:5000`**
- **Test Skewed Bottleneck** button dabakar dekhiye: Gantt chart mein Core 0 laal (heavy) blocks se bhara hoga aur Core 1–3 mein bade idle gaps honge.
- **Test Balanced Workload** button dabakar dekhiye: Chaaron cores par barabar kaam hoga aur 97%+ utilization milegi!
