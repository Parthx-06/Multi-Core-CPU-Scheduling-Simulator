// Multi-Core CPU Scheduling Simulator - Phase 2 Dashboard
let loadChart = null;
let queueChart = null;

const elements = {
  schedulerMode: document.getElementById('scheduler-mode'),
  workloadType: document.getElementById('workload-type'),
  numCores: document.getElementById('num-cores'),
  policy: document.getElementById('policy'),
  migrationPenalty: document.getElementById('migration-penalty'),
  numTasks: document.getElementById('num-tasks'),
  taskCountVal: document.getElementById('task-count-val'),
  workloadDesc: document.getElementById('workload-desc'),
  btnSimulate: document.getElementById('btn-simulate'),
  btnQuickPhase1: document.getElementById('btn-quick-phase1'),
  btnQuickPhase2: document.getElementById('btn-quick-phase2'),
  btnRefreshBenchmarks: document.getElementById('btn-refresh-benchmarks'),
  
  // Metric values
  valImbalance: document.getElementById('val-imbalance'),
  subJains: document.getElementById('sub-jains'),
  valSpeedup: document.getElementById('val-speedup'),
  subEfficiency: document.getElementById('sub-efficiency'),
  valMakespan: document.getElementById('val-makespan'),
  sub1core: document.getElementById('sub-1core'),
  valResponse: document.getElementById('val-response'),
  subWait: document.getElementById('sub-wait'),
  valUtilization: document.getElementById('val-utilization'),
  subMigrations: document.getElementById('sub-migrations'),

  ganttContainer: document.getElementById('gantt-container'),
  comparisonTbody: document.getElementById('comparison-tbody')
};

// Workload descriptions
const descriptions = {
  skewed_hotspot: "Every 4th task has 6x burst, overloading Core 0 in Static Round-Robin.",
  skewed_bimodal: "80% short mouse tasks + 20% massive elephant tasks arriving in bursts.",
  balanced: "Uniform burst distributions with evenly spaced task arrivals across all cores."
};

// Initialize event listeners
function init() {
  elements.numTasks.addEventListener('input', (e) => {
    elements.taskCountVal.textContent = e.target.value;
  });

  elements.workloadType.addEventListener('change', (e) => {
    elements.workloadDesc.textContent = descriptions[e.target.value] || "";
  });

  elements.btnSimulate.addEventListener('click', () => runSimulation());

  elements.btnQuickPhase1.addEventListener('click', () => {
    elements.schedulerMode.value = 'static';
    elements.workloadType.value = 'skewed_hotspot';
    elements.workloadDesc.textContent = descriptions.skewed_hotspot;
    elements.policy.value = 'round_robin';
    elements.numCores.value = '4';
    runSimulation();
  });

  elements.btnQuickPhase2.addEventListener('click', () => {
    elements.schedulerMode.value = 'dynamic';
    elements.workloadType.value = 'skewed_hotspot';
    elements.workloadDesc.textContent = descriptions.skewed_hotspot;
    elements.policy.value = 'round_robin';
    elements.numCores.value = '4';
    elements.migrationPenalty.value = '1';
    runSimulation();
  });

  elements.btnRefreshBenchmarks.addEventListener('click', () => loadComparisonTable());

  // Initial loads
  loadComparisonTable();
  runSimulation();
}

// Run simulation via backend API
async function runSimulation() {
  elements.btnSimulate.disabled = true;
  elements.btnSimulate.innerHTML = `<span class="btn-icon">⏳</span> Simulating...`;

  try {
    const payload = {
      scheduler_mode: elements.schedulerMode.value,
      workload_type: elements.workloadType.value,
      num_cores: parseInt(elements.numCores.value),
      num_tasks: parseInt(elements.numTasks.value),
      policy: elements.policy.value,
      migration_penalty: parseInt(elements.migrationPenalty.value),
      imbalance_threshold: 15.0,
      prediction_horizon: 10,
      seed: 42
    };

    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Simulation failed');
    const data = await res.json();
    renderSimulationResults(data);
  } catch (err) {
    console.error(err);
    alert('Failed to run simulation. Ensure the Flask server is running.');
  } finally {
    elements.btnSimulate.disabled = false;
    elements.btnSimulate.innerHTML = `<span class="btn-icon">▶</span> Run Simulation`;
  }
}

// Render metrics, charts, and Gantt
function renderSimulationResults(data) {
  const m = data.metrics;
  const imb = m.load_imbalance;

  // 1. Update metric cards
  elements.valImbalance.textContent = `${imb.std_dev_busy_ticks} ticks`;
  elements.subJains.textContent = `Jain's Fairness Index: ${imb.jains_fairness_index.toFixed(3)}`;

  elements.valSpeedup.textContent = m.speedup ? `${m.speedup.toFixed(2)}x` : '1.00x';
  elements.subEfficiency.textContent = m.efficiency_pct ? `Efficiency: ${m.efficiency_pct.toFixed(1)}%` : 'Efficiency: 100%';

  elements.valMakespan.textContent = `${m.makespan} ticks`;
  elements.sub1core.textContent = `Single Core: ${m.single_core_makespan || '--'} ticks`;

  elements.valResponse.textContent = `${m.response_time.mean.toFixed(1)} / ${m.response_time.p95.toFixed(1)} t`;
  elements.subWait.textContent = `Avg Wait Time: ${m.waiting_time.mean.toFixed(1)} ticks`;

  elements.valUtilization.textContent = `${m.cpu_utilization.average_pct.toFixed(1)}%`;
  
  if (data.scheduler_mode === 'dynamic') {
    const totalMig = m.migrations ? m.migrations.total_count : (data.migrations ? data.migrations.length : 0);
    const overhead = m.migrations ? m.migrations.total_overhead_ticks : 0;
    elements.subMigrations.textContent = `Dynamic Migrations: ${totalMig} (Overhead: ${overhead}t)`;
  } else {
    elements.subMigrations.textContent = `Static Mode: 0 Migrations`;
  }

  // 2. Render Gantt view
  currentSimTasks = data.tasks || [];
  currentMigrations = data.migrations || [];
  const migratedTaskIds = new Set((data.migrations || []).map(mig => mig.task_id));
  renderGantt(data.timelines, m.makespan, migratedTaskIds);

  // 3. Render Charts
  renderCoreLoadChart(imb.core_busy_ticks, imb.core_idle_ticks, data.num_cores);
  renderQueueChart(data.timelines, data.num_cores);
}

// Gantt timeline renderer
function renderGantt(timelines, makespan, migratedTaskIds) {
  elements.ganttContainer.innerHTML = '';
  const coreKeys = Object.keys(timelines).sort();

  coreKeys.forEach(coreKey => {
    const ticks = timelines[coreKey];
    const coreId = coreKey.replace('core_', '');

    const row = document.createElement('div');
    row.className = 'core-row';

    const label = document.createElement('div');
    label.className = 'core-label';
    label.textContent = `Core ${coreId}`;
    row.appendChild(label);

    const track = document.createElement('div');
    track.className = 'core-track';

    // Compress consecutive identical states into blocks
    if (ticks && ticks.length > 0) {
      let currentBlock = {
        taskId: ticks[0].task_id,
        state: ticks[0].state,
        duration: 1
      };

      for (let i = 1; i < ticks.length; i++) {
        const t = ticks[i];
        if (t.task_id === currentBlock.taskId && t.state === currentBlock.state) {
          currentBlock.duration++;
        } else {
          appendGanttBlock(track, currentBlock, makespan, migratedTaskIds);
          currentBlock = {
            taskId: t.task_id,
            state: t.state,
            duration: 1
          };
        }
      }
      appendGanttBlock(track, currentBlock, makespan, migratedTaskIds);
    }

    row.appendChild(track);
    elements.ganttContainer.appendChild(row);
  });
}

let currentSimTasks = [];
let currentMigrations = [];

function inspectTask(taskId) {
  const inspector = document.getElementById('task-inspector');
  if (!inspector || taskId === null || taskId === undefined) return;

  const task = currentSimTasks.find(t => t.task_id === taskId);
  if (!task) return;

  inspector.style.display = 'block';
  const title = document.getElementById('inspector-task-title');
  const badge = document.getElementById('inspector-badge');
  const grid = document.getElementById('inspector-grid');

  title.textContent = `Task #${task.task_id} Execution Trace`;

  const migrationRecord = currentMigrations.find(m => m.task_id === task.task_id);
  if (migrationRecord) {
    badge.textContent = `MIGRATED (Core ${migrationRecord.from_core} → Core ${migrationRecord.to_core})`;
    badge.className = 'badge badge-phase';
  } else {
    badge.textContent = task.tag === 'heavy' ? 'HEAVY BURST' : 'NORMAL';
    badge.className = task.tag === 'heavy' ? 'badge delta-negative' : 'badge badge-sub';
  }

  grid.innerHTML = `
    <div class="inspector-item">
      <span class="inspector-label">Arrival Tick</span>
      <span class="inspector-val">Tick ${task.arrival_time}</span>
    </div>
    <div class="inspector-item">
      <span class="inspector-label">Burst Workload</span>
      <span class="inspector-val">${task.burst_time} cycles</span>
    </div>
    <div class="inspector-item">
      <span class="inspector-label">Executing Core</span>
      <span class="inspector-val">Core ${task.assigned_core_id}</span>
    </div>
    <div class="inspector-item">
      <span class="inspector-label">Start Tick</span>
      <span class="inspector-val">Tick ${task.start_time ?? '--'}</span>
    </div>
    <div class="inspector-item">
      <span class="inspector-label">Wait / Response Time</span>
      <span class="inspector-val">${task.response_time ?? '--'} ticks</span>
    </div>
    <div class="inspector-item">
      <span class="inspector-label">Completion Tick</span>
      <span class="inspector-val">Tick ${task.completion_time ?? '--'}</span>
    </div>
    <div class="inspector-item">
      <span class="inspector-label">Turnaround Time</span>
      <span class="inspector-val">${task.turnaround_time ?? '--'} ticks</span>
    </div>
    <div class="inspector-item">
      <span class="inspector-label">Dynamic Migrations</span>
      <span class="inspector-val">${task.migration_count || (migrationRecord ? 1 : 0)} times</span>
    </div>
  `;
}

function appendGanttBlock(track, block, totalMakespan, migratedTaskIds) {
  const div = document.createElement('div');
  const widthPct = Math.max(0.4, (block.duration / totalMakespan) * 100);
  div.style.width = `${widthPct}%`;

  if (block.state === 'IDLE') {
    div.className = 'gantt-block block-idle';
    div.title = `Core Idle (${block.duration} ticks)`;
    if (widthPct > 5) div.textContent = 'idle';
  } else if (block.state === 'MIGRATING') {
    div.className = 'gantt-block block-migrating';
    div.title = `Migration Context Penalty (${block.duration} ticks)`;
    if (widthPct > 4) div.textContent = 'mig';
  } else {
    // Task execution block
    const isMigrated = migratedTaskIds.has(block.taskId);
    if (isMigrated) {
      div.className = 'gantt-block block-migrated';
      div.title = `[Click to Inspect] Migrated Task #${block.taskId} (${block.duration} ticks)`;
      if (widthPct > 3) div.textContent = `T${block.taskId}*`;
    } else {
      div.className = block.duration >= 20 ? 'gantt-block block-heavy' : 'gantt-block block-light';
      div.title = `[Click to Inspect] Task #${block.taskId} (${block.duration} ticks)`;
      if (widthPct > 3) div.textContent = `T${block.taskId}`;
    }

    div.addEventListener('click', () => inspectTask(block.taskId));
  }

  track.appendChild(div);
}

// Chart 1: Per-core Busy vs Idle
function renderCoreLoadChart(busyTicks, idleTicks, numCores) {
  const ctx = document.getElementById('chart-core-load').getContext('2d');
  const labels = Array.from({ length: numCores }, (_, i) => `Core ${i}`);

  if (loadChart) loadChart.destroy();

  loadChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Busy Cycles',
          data: busyTicks,
          backgroundColor: '#06b6d4',
          borderRadius: 4
        },
        {
          label: 'Idle Cycles',
          data: idleTicks,
          backgroundColor: '#1e293b',
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          stacked: true,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' }
        },
        y: {
          stacked: true,
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' }
        }
      },
      plugins: {
        legend: { labels: { color: '#cbd5e1' } }
      }
    }
  });
}

// Chart 2: Queue Dynamics
function renderQueueChart(timelines, numCores) {
  const ctx = document.getElementById('chart-queue-dynamics').getContext('2d');
  if (queueChart) queueChart.destroy();

  const colors = ['#06b6d4', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#ec4899', '#8b5cf6'];
  const coreKeys = Object.keys(timelines).sort();

  // Downsample for smooth rendering
  const sampleStep = Math.max(1, Math.floor((timelines[coreKeys[0]]?.length || 100) / 80));
  const labels = [];
  const datasets = coreKeys.map((key, idx) => {
    const ticks = timelines[key] || [];
    const sampledData = [];
    for (let i = 0; i < ticks.length; i += sampleStep) {
      if (idx === 0) labels.push(ticks[i].tick);
      sampledData.push(ticks[i].queue_len);
    }
    return {
      label: `Core ${key.replace('core_', '')} Queue`,
      data: sampledData,
      borderColor: colors[idx % colors.length],
      backgroundColor: 'transparent',
      borderWidth: 2,
      tension: 0.2,
      pointRadius: 0
    };
  });

  queueChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: { display: true, text: 'Simulation Tick', color: '#94a3b8' },
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8', maxTicksLimit: 10 }
        },
        y: {
          title: { display: true, text: 'Queue Length (tasks)', color: '#94a3b8' },
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' }
        }
      },
      plugins: {
        legend: { labels: { color: '#cbd5e1' } }
      }
    }
  });
}

// Load Phase 1 vs Phase 2 Comparison Table
async function loadComparisonTable() {
  try {
    const res = await fetch('/api/phase2_comparison');
    if (!res.ok) return;
    const data = await res.json();
    
    elements.comparisonTbody.innerHTML = '';
    const h = data.skewed_hotspot;
    if (!h) return;

    const s = h.static;
    const d = h.dynamic;
    const c = h.comparison;

    const rows = [
      {
        metric: "Makespan (Total Execution Ticks)",
        phase1: `${s.makespan} t`,
        phase2: `${d.makespan} t`,
        delta: `-${c.makespan_reduction_pct.toFixed(1)}% reduction`,
        isPositive: true
      },
      {
        metric: "Speedup (relative to 1-Core baseline)",
        phase1: `${s.speedup.toFixed(2)}x`,
        phase2: `${d.speedup.toFixed(2)}x`,
        delta: `+${c.speedup_gain.toFixed(2)}x speedup gain`,
        isPositive: true
      },
      {
        metric: "Multi-Core Efficiency (%)",
        phase1: `${s.efficiency_pct.toFixed(1)}%`,
        phase2: `${d.efficiency_pct.toFixed(1)}%`,
        delta: `+${(d.efficiency_pct - s.efficiency_pct).toFixed(1)}% efficiency boost`,
        isPositive: true
      },
      {
        metric: "Load Imbalance (StdDev of busy cycles)",
        phase1: `${s.load_imbalance.std_dev_busy_ticks.toFixed(1)} ticks`,
        phase2: `${d.load_imbalance.std_dev_busy_ticks.toFixed(1)} ticks`,
        delta: `-${c.imbalance_reduction_pct.toFixed(1)}% imbalance drop`,
        isPositive: true
      },
      {
        metric: "Jain's Fairness Index (0.0 to 1.0)",
        phase1: `${s.load_imbalance.jains_fairness_index.toFixed(3)}`,
        phase2: `${d.load_imbalance.jains_fairness_index.toFixed(3)}`,
        delta: `+${c.fairness_gain.toFixed(3)} (restored to 1.0)`,
        isPositive: true
      },
      {
        metric: "P95 Response Latency",
        phase1: `${s.response_time.p95.toFixed(1)} ticks`,
        phase2: `${d.response_time.p95.toFixed(1)} ticks`,
        delta: `-${c.p95_resp_reduction_pct.toFixed(1)}% tail latency drop`,
        isPositive: true
      },
      {
        metric: "Average CPU Core Utilization",
        phase1: `${s.cpu_utilization.average_pct.toFixed(1)}%`,
        phase2: `${d.cpu_utilization.average_pct.toFixed(1)}%`,
        delta: `+${(d.cpu_utilization.average_pct - s.cpu_utilization.average_pct).toFixed(1)}% utilization`,
        isPositive: true
      },
      {
        metric: "Dynamic Task Migrations",
        phase1: "0 (Static)",
        phase2: `${c.total_migrations} tasks migrated`,
        delta: `Overhead: ${d.migrations ? d.migrations.total_overhead_ticks : 0}t`,
        isPositive: true
      }
    ];

    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${r.metric}</strong></td>
        <td style="color: #ef4444; font-weight: 600;">${r.phase1}</td>
        <td style="color: #10b981; font-weight: 700;">${r.phase2}</td>
        <td><span class="delta-pill ${r.isPositive ? 'delta-positive' : 'delta-negative'}">${r.delta}</span></td>
      `;
      elements.comparisonTbody.appendChild(tr);
    });

  } catch (err) {
    console.error('Failed to load comparison data', err);
  }
}

// Startup
window.addEventListener('DOMContentLoaded', init);
