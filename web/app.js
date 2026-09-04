// Multi-Core CPU Scheduling Simulator - Phase 1 Dashboard
let loadChart = null;
let queueChart = null;

const elements = {
  workloadType: document.getElementById('workload-type'),
  numCores: document.getElementById('num-cores'),
  policy: document.getElementById('policy'),
  numTasks: document.getElementById('num-tasks'),
  taskCountVal: document.getElementById('task-count-val'),
  workloadDesc: document.getElementById('workload-desc'),
  btnSimulate: document.getElementById('btn-simulate'),
  btnQuickSkew: document.getElementById('btn-quick-skew'),
  btnQuickBalanced: document.getElementById('btn-quick-balanced'),
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
  subThroughput: document.getElementById('sub-throughput'),

  ganttContainer: document.getElementById('gantt-container'),
  benchmarksTbody: document.getElementById('benchmarks-tbody')
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

  elements.btnQuickSkew.addEventListener('click', () => {
    elements.workloadType.value = 'skewed_hotspot';
    elements.workloadDesc.textContent = descriptions.skewed_hotspot;
    elements.policy.value = 'round_robin';
    elements.numCores.value = '4';
    runSimulation();
  });

  elements.btnQuickBalanced.addEventListener('click', () => {
    elements.workloadType.value = 'balanced';
    elements.workloadDesc.textContent = descriptions.balanced;
    elements.policy.value = 'round_robin';
    elements.numCores.value = '4';
    runSimulation();
  });

  elements.btnRefreshBenchmarks.addEventListener('click', () => loadBenchmarks());

  // Initial loads
  loadBenchmarks();
  runSimulation();
}

// Run simulation via backend API
async function runSimulation() {
  elements.btnSimulate.disabled = true;
  elements.btnSimulate.innerHTML = `<span class="btn-icon">⏳</span> Simulating...`;

  try {
    const payload = {
      workload_type: elements.workloadType.value,
      num_cores: parseInt(elements.numCores.value),
      num_tasks: parseInt(elements.numTasks.value),
      policy: elements.policy.value,
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
  elements.subThroughput.textContent = `Throughput: ${m.throughput_per_100_ticks} tasks/100t`;

  // 2. Render Gantt view
  renderGantt(data.timelines, m.makespan);

  // 3. Render Charts
  renderCoreLoadChart(imb.core_busy_ticks, imb.core_idle_ticks, data.num_cores);
  renderQueueChart(data.timelines, data.num_cores);
}

// Gantt timeline renderer
function renderGantt(timelines, makespan) {
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
          appendGanttBlock(track, currentBlock, makespan);
          currentBlock = {
            taskId: t.task_id,
            state: t.state,
            duration: 1
          };
        }
      }
      appendGanttBlock(track, currentBlock, makespan);
    }

    row.appendChild(track);
    elements.ganttContainer.appendChild(row);
  });
}

function appendGanttBlock(track, block, totalMakespan) {
  const div = document.createElement('div');
  const widthPct = Math.max(0.5, (block.duration / totalMakespan) * 100);
  div.style.width = `${widthPct}%`;

  if (block.state === 'IDLE') {
    div.className = 'gantt-block block-idle';
    div.title = `Core Idle (${block.duration} ticks)`;
    if (widthPct > 5) div.textContent = 'idle';
  } else {
    // Check if heavy (>20 ticks) or light
    div.className = block.duration >= 20 ? 'gantt-block block-heavy' : 'gantt-block block-light';
    div.title = `Task #${block.taskId} (${block.duration} ticks)`;
    if (widthPct > 3) div.textContent = `T${block.taskId}`;
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

  // Downsample to max 100 points for smooth charting
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

// Load static benchmark results table
async function loadBenchmarks() {
  try {
    const res = await fetch('/api/benchmarks');
    if (!res.ok) return;
    const benchmarks = await res.json();
    
    elements.benchmarksTbody.innerHTML = '';
    
    for (const [wKey, wData] of Object.entries(benchmarks)) {
      wData.runs.forEach(run => {
        const m = run.metrics;
        const tr = document.createElement('tr');
        
        const isSkewedHotspot = run.workload.includes('hotspot');
        const isBadImbalance = m.load_imbalance.jains_fairness_index < 0.7;

        tr.innerHTML = `
          <td><strong>${wData.workload_name}</strong></td>
          <td>${run.policy.replace('_', ' ')}</td>
          <td>${run.num_cores}</td>
          <td>${m.makespan}</td>
          <td><span style="color: ${m.speedup > 3 ? '#10b981' : '#f59e0b'}">${m.speedup ? m.speedup.toFixed(2) + 'x' : '1.00x'}</span></td>
          <td>${m.efficiency_pct ? m.efficiency_pct.toFixed(1) + '%' : '100%'}</td>
          <td style="color: ${isBadImbalance ? '#ef4444' : '#94a3b8'}">${m.load_imbalance.std_dev_busy_ticks.toFixed(1)}</td>
          <td style="color: ${isBadImbalance ? '#ef4444' : '#10b981'}; font-weight: 600;">${m.load_imbalance.jains_fairness_index.toFixed(3)}</td>
          <td>${m.response_time.mean.toFixed(1)}</td>
          <td>${m.response_time.p95.toFixed(1)}</td>
          <td>${m.cpu_utilization.average_pct.toFixed(1)}%</td>
        `;
        elements.benchmarksTbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.error('Failed to load benchmarks', err);
  }
}

// Startup
window.addEventListener('DOMContentLoaded', init);
