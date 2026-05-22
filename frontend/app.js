/* ─────────────────────────────────────────────────────────────────
   ReturnGuard AI — Frontend Application Logic
   ───────────────────────────────────────────────────────────────── */

const API_BASE = '';   // same origin

// ── Colour palettes per customer ──────────────────────────────────
const AVATAR_PALETTES = [
  { bg: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', color: '#fff' },
  { bg: 'linear-gradient(135deg,#ec4899,#f97316)', color: '#fff' },
  { bg: 'linear-gradient(135deg,#10b981,#06b6d4)', color: '#fff' },
  { bg: 'linear-gradient(135deg,#ef4444,#f59e0b)', color: '#fff' },
  { bg: 'linear-gradient(135deg,#8b5cf6,#06b6d4)', color: '#fff' },
];

// ── Action metadata ───────────────────────────────────────────────
const ACTION_META = {
  PROCEED:       { icon: '✅', label: 'Return Approved',          colorClass: 'action-PROCEED',       textClass: 'text-green'  },
  SEND_AGENT:    { icon: '👤', label: 'Agent Verification Required', colorClass: 'action-SEND_AGENT',  textClass: 'text-amber'  },
  ASK_VIDEO:     { icon: '🎥', label: 'Video Proof Required',     colorClass: 'action-ASK_VIDEO',     textClass: 'text-violet' },
  CUSTOMER_CARE: { icon: '📞', label: 'Escalate to Customer Care', colorClass: 'action-CUSTOMER_CARE', textClass: 'text-red'    },
  MONITORING:    { icon: '📊', label: 'Approved with Monitoring',  colorClass: 'action-MONITORING',    textClass: 'text-blue'   },
  MANUAL_REVIEW: { icon: '🔍', label: 'Manual Review Required',   colorClass: 'action-MANUAL_REVIEW', textClass: 'text-red'    },
};

const IMAGE_STATUS_META = {
  AUTHENTIC:  { dot: '#10b981', label: 'Authentic',  cls: 'text-green'  },
  SUSPICIOUS: { dot: '#f59e0b', label: 'Suspicious', cls: 'text-amber'  },
  FAKE:       { dot: '#ef4444', label: 'Fake',       cls: 'text-red'    },
  UNKNOWN:    { dot: '#94a3b8', label: 'Unknown',    cls: 'text-secondary' },
};

const RISK_META = {
  LOW:    { color: '#10b981', bg: 'rgba(16,185,129,0.15)'  },
  MEDIUM: { color: '#f59e0b', bg: 'rgba(245,158,11,0.15)'  },
  HIGH:   { color: '#ef4444', bg: 'rgba(239,68,68,0.15)'   },
};

const FEATURE_LABELS = {
  total_orders_count:   'Total Orders',
  total_returns_count:  'Total Returns',
  account_age:          'Account Age (days)',
  average_return_time:  'Avg Return Time (days)',
  fraud_history_flag:   'Fraud History Flag',
};

// ── State ─────────────────────────────────────────────────────────
let demoCustomers = [];
let activeCustomerId = null;
let lastResult = null;
let loadingTimer = null;

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadDemoCustomers();
  setupForm();
  setupUploadZone();
});

async function loadDemoCustomers() {
  try {
    const res = await fetch(`${API_BASE}/api/demo-customers`);
    demoCustomers = await res.json();
    renderCustomerList();
  } catch (e) {
    console.error('Failed to load demo customers', e);
  }
}

function renderCustomerList() {
  const list = document.getElementById('customerList');
  list.innerHTML = demoCustomers.map((c, i) => {
    const palette = AVATAR_PALETTES[i % AVATAR_PALETTES.length];
    const initials = c.name.split(' ').map(n => n[0]).join('').slice(0, 2);
    const badgeClass = c.return_type === 'return' ? 'badge-return' : 'badge-returnless';
    const badgeLabel = c.return_type === 'return' ? 'Return' : 'Returnless';
    const fraudBadge = c.fraud_history_flag ? '<span style="font-size:10px;color:#ef4444;font-weight:700">⚠ FRAUD HISTORY</span>' : '';
    return `
      <div class="customer-card" id="cc-${c.id}" onclick="runDemoCustomer('${c.id}', ${i})">
        <div class="customer-avatar" style="background:${palette.bg};color:${palette.color}">${initials}</div>
        <div class="customer-info">
          <div class="customer-name">${c.name}</div>
          <div class="customer-product">${c.product}</div>
          <div class="customer-price">Orders: ${c.total_orders_count} &nbsp;|&nbsp; Returns: ${c.total_returns_count} ${fraudBadge}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
          <span class="customer-badge ${badgeClass}">${badgeLabel}</span>
        </div>
      </div>`;
  }).join('');
}

// ── Demo Customer Run ─────────────────────────────────────────────
async function runDemoCustomer(customerId, idx) {
  if (activeCustomerId === customerId) return;
  activeCustomerId = customerId;

  // Mark active
  document.querySelectorAll('.customer-card').forEach(el => el.classList.remove('active'));
  const card = document.getElementById(`cc-${customerId}`);
  if (card) card.classList.add('active', 'customer-loading');

  showLoading();

  try {
    const res = await fetch(`${API_BASE}/api/validate-demo/${customerId}`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    lastResult = data;
    renderResults(data, idx);
  } catch (e) {
    showError(e.message || 'An unexpected error occurred.');
  } finally {
    if (card) card.classList.remove('customer-loading');
  }
}

// ── Form Submit ───────────────────────────────────────────────────
function setupForm() {
  document.getElementById('validateForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    activeCustomerId = null;
    document.querySelectorAll('.customer-card').forEach(el => el.classList.remove('active'));

    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    showLoading();

    const form = e.target;
    const fd = new FormData(form);

    // Check if file uploaded
    const fileInput = document.getElementById('imageFile');
    if (fileInput.files[0]) {
      fd.set('image', fileInput.files[0]);
    } else {
      fd.delete('image');
      const url = document.getElementById('imageUrl').value.trim();
      if (url) fd.set('image_url', url);
    }

    try {
      const res = await fetch(`${API_BASE}/api/validate`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      lastResult = data;
      const customData = {
        customer: {
          id: 'CUSTOM',
          name: 'Custom Request',
          product: 'Manual Entry',
          total_orders_count: parseInt(fd.get('total_orders_count')) || 0,
          total_returns_count: parseInt(fd.get('total_returns_count')) || 0,
          account_age: parseInt(fd.get('account_age')) || 0,
          average_return_time: parseInt(fd.get('average_return_time')) || 0,
          fraud_history_flag: parseInt(fd.get('fraud_history_flag')) || 0,
          return_type: fd.get('return_type'),
        },
        ...data,
      };
      renderResults(customData, 0);
    } catch (err) {
      showError(err.message || 'Validation failed.');
    } finally {
      btn.disabled = false;
    }
  });
}

// ── Upload Zone ───────────────────────────────────────────────────
function setupUploadZone() {
  const zone = document.getElementById('uploadZone');
  const input = document.getElementById('imageFile');
  const label = document.getElementById('uploadLabel');

  input.addEventListener('change', () => {
    if (input.files[0]) {
      label.textContent = `📎 ${input.files[0].name}`;
      zone.style.borderColor = 'var(--accent-blue)';
    }
  });

  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      label.textContent = `📎 ${file.name}`;
      zone.style.borderColor = 'var(--accent-blue)';
    }
  });
}

// ── UI State Controllers ──────────────────────────────────────────
function showLoading() {
  hide('emptyState'); hide('resultsPanel'); hide('errorState');
  show('loadingState');

  // Animate loading steps
  const dots = ['step1','step2','step3'];
  dots.forEach(id => {
    const dot = document.querySelector(`#${id} .step-dot`);
    if (dot) dot.className = 'step-dot';
  });

  let step = 0;
  clearInterval(loadingTimer);
  loadingTimer = setInterval(() => {
    if (step < dots.length) {
      const prev = step > 0 ? document.querySelector(`#${dots[step-1]} .step-dot`) : null;
      if (prev) { prev.className = 'step-dot done'; document.getElementById(dots[step-1]).classList.add('done-step'); }
      document.querySelector(`#${dots[step]} .step-dot`).className = 'step-dot active';
      step++;
    } else {
      clearInterval(loadingTimer);
    }
  }, 700);
}

function showError(msg) {
  clearInterval(loadingTimer);
  hide('loadingState'); hide('resultsPanel'); hide('emptyState');
  show('errorState');
  document.getElementById('errorMessage').textContent = msg;
}

function resetUI() {
  hide('errorState'); hide('resultsPanel'); hide('loadingState');
  show('emptyState');
  activeCustomerId = null;
  document.querySelectorAll('.customer-card').forEach(el => el.classList.remove('active'));
}

// ── Render Results ────────────────────────────────────────────────
function renderResults(data, avatarIdx = 0) {
  clearInterval(loadingTimer);
  hide('loadingState'); hide('emptyState'); hide('errorState');
  show('resultsPanel');

  const c       = data.customer || {};
  const imgMeta = IMAGE_STATUS_META[data.image_status] || IMAGE_STATUS_META.UNKNOWN;
  const rkMeta  = RISK_META[data.risk_level] || RISK_META.MEDIUM;
  const actMeta = ACTION_META[data.action]   || ACTION_META.MANUAL_REVIEW;
  const palette = AVATAR_PALETTES[avatarIdx % AVATAR_PALETTES.length];
  const initials = (c.name || 'C').split(' ').map(n => n[0]).join('').slice(0, 2);

  // ── Header ──────────────────────────────────────────────────────
  document.getElementById('resultHeader').innerHTML = `
    <div class="rh-avatar" style="background:${palette.bg}">${initials}</div>
    <div class="rh-info">
      <div class="rh-name">${c.name || 'Custom Request'}</div>
      <div class="rh-product">${c.product || '\u2014'}</div>
      <div class="rh-price">Orders: ${c.total_orders_count ?? '\u2014'} &nbsp;|&nbsp; Returns: ${c.total_returns_count ?? '\u2014'} &nbsp;|&nbsp; Acct Age: ${c.account_age ?? '\u2014'}d</div>
    </div>
    <div class="rh-meta">
      <span class="tag">${c.return_type === 'returnless' ? '\uD83D\uDD04 Returnless' : '\uD83D\uDCE6 Return'}</span>
    </div>`;

  // ── Action Banner ────────────────────────────────────────────────
  document.getElementById('actionBanner').className = `action-banner ${actMeta.colorClass}`;
  document.getElementById('actionBanner').innerHTML = `
    <div class="ab-icon">${actMeta.icon}</div>
    <div class="ab-content">
      <div class="ab-label">Recommended Action</div>
      <div class="ab-action ${actMeta.textClass}">${actMeta.label}</div>
      <span class="ab-severity sev-${data.severity}">${data.severity} SEVERITY</span>
    </div>
    <div style="text-align:right">
      <div style="font-size:11px;color:var(--text-muted);font-weight:600;letter-spacing:.5px">ACTION CODE</div>
      <div style="font-size:18px;font-weight:800;font-family:var(--font-mono);letter-spacing:1px;margin-top:4px">${data.action}</div>
    </div>`;

  // ── Stats ────────────────────────────────────────────────────────
  const conf = data.confidence != null ? (data.confidence * 100).toFixed(1) + '%' : 'N/A';
  document.getElementById('statImage').innerHTML = `
    <div class="stat-label">Image Status</div>
    <div class="stat-value ${imgMeta.cls}" style="font-size:18px;font-weight:800">${imgMeta.label}</div>
    <div class="stat-sub"><span class="stat-dot" style="background:${imgMeta.dot}"></span>Hive AI Result</div>`;

  document.getElementById('statConfidence').innerHTML = `
    <div class="stat-label">Confidence</div>
    <div class="stat-value" style="color:${imgMeta.dot}">${conf}</div>
    <div class="stat-sub">Detection confidence</div>`;

  document.getElementById('statRisk').innerHTML = `
    <div class="stat-label">ML Risk Score</div>
    <div class="stat-value" style="color:${rkMeta.color}">${(data.risk_score * 100).toFixed(1)}%</div>
    <div class="stat-sub">${data.risk_level} risk level</div>`;

  document.getElementById('statPrice').innerHTML = `
    <div class="stat-label">Fraud History</div>
    <div class="stat-value ${c.fraud_history_flag ? 'text-red' : 'text-green'}" style="font-size:18px">${c.fraud_history_flag ? '⚠ Yes' : '✓ None'}</div>
    <div class="stat-sub">Acct Age: ${c.account_age ?? '—'}d</div>`;

  // ── Gauge Canvas ─────────────────────────────────────────────────
  drawGauge(data.confidence, data.image_status);

  // ── Image Score Bars ─────────────────────────────────────────────
  const realScore = data.real_score != null ? data.real_score : (data.confidence && !data.is_deepfake ? data.confidence : null);
  const fakeScore = data.fake_score != null ? data.fake_score : (data.confidence && data.is_deepfake ? data.confidence : null);

  document.getElementById('imageBars').innerHTML = `
    ${scoreBar('Real Score', realScore, '#10b981')}
    ${scoreBar('Fake Score', fakeScore, '#ef4444')}`;

  // Hive tag
  const hiveTagColor = data.hive_status === 'ok' ? '#10b981' : '#ef4444';
  document.getElementById('hiveTag').innerHTML = `
    <span style="color:${hiveTagColor};font-weight:700">● Hive AI</span>
    &nbsp;|&nbsp; status: <b>${data.hive_status}</b>
    ${data.hive_error ? `&nbsp;| ⚠ ${data.hive_error}` : ''}`;

  // ── Risk Meter ────────────────────────────────────────────────────
  const riskPct = (data.risk_score * 100).toFixed(1);
  document.getElementById('riskMeter').innerHTML = `
    <div class="risk-score-big" style="color:${rkMeta.color}">${riskPct}%</div>
    <span class="risk-level-badge" style="background:${rkMeta.bg};color:${rkMeta.color}">${data.risk_level} RISK</span>
    <div class="risk-bar-track" style="position:relative">
      <div class="risk-indicator" style="left:${riskPct}%"></div>
    </div>
    <div class="risk-labels"><span>Low</span><span>Medium</span><span>High</span></div>`;

  // ── Feature Importances ───────────────────────────────────────────
  const fi = data.feature_importances || {};
  const sorted = Object.entries(fi).sort((a, b) => b[1] - a[1]);
  const maxFI = sorted[0]?.[1] || 1;
  document.getElementById('featureChart').innerHTML = sorted.slice(0, 8).map(([key, val]) => `
    <div class="fi-row">
      <span class="fi-label">${FEATURE_LABELS[key] || key}</span>
      <div class="fi-bar-track"><div class="fi-bar-fill" style="width:${(val/maxFI)*100}%"></div></div>
      <span class="fi-val">${(val*100).toFixed(1)}%</span>
    </div>`).join('');

  // ── Explanation ───────────────────────────────────────────────────
  document.getElementById('explanationPanel').innerHTML = `
    <div class="exp-title">📋 Decision Explanation</div>
    <div class="exp-body">${data.reason}</div>`;

  // ── Decision Flow ─────────────────────────────────────────────────
  renderFlow(data);
}

// ── Gauge Canvas ──────────────────────────────────────────────────
function drawGauge(confidence, imageStatus) {
  const canvas = document.getElementById('gaugeCanvas');
  const ctx = canvas.getContext('2d');
  const cx = 100, cy = 100, r = 75, lw = 14;

  ctx.clearRect(0, 0, 200, 110);

  // Background arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, 0, false);
  ctx.strokeStyle = 'rgba(255,255,255,0.07)';
  ctx.lineWidth = lw;
  ctx.lineCap = 'round';
  ctx.stroke();

  if (confidence == null) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, Math.PI * 1.5, false);
    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = lw; ctx.lineCap = 'round';
    ctx.stroke();
  } else {
    // Gradient arc
    const grad = ctx.createLinearGradient(cx - r, 0, cx + r, 0);
    const statusColors = { AUTHENTIC: '#10b981', SUSPICIOUS: '#f59e0b', FAKE: '#ef4444', UNKNOWN: '#94a3b8' };
    const color = statusColors[imageStatus] || '#3b82f6';
    grad.addColorStop(0, color + '88');
    grad.addColorStop(1, color);

    const endAngle = Math.PI + (confidence * Math.PI);
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, endAngle, false);
    ctx.strokeStyle = grad;
    ctx.lineWidth = lw; ctx.lineCap = 'round';
    ctx.stroke();
  }

  // Center text
  ctx.font = 'bold 22px Inter, sans-serif';
  ctx.fillStyle = '#f1f5f9';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const label = confidence != null ? (confidence * 100).toFixed(0) + '%' : 'N/A';
  ctx.fillText(label, cx, cy - 6);
  ctx.font = '11px Inter, sans-serif';
  ctx.fillStyle = '#94a3b8';
  ctx.fillText(imageStatus || 'UNKNOWN', cx, cy + 16);
}

// ── Score Bar Helper ──────────────────────────────────────────────
function scoreBar(label, value, color) {
  const pct = value != null ? (value * 100).toFixed(1) : 0;
  const display = value != null ? pct + '%' : 'N/A';
  return `
    <div class="score-bar-row">
      <div class="score-bar-label">
        <span style="color:${color}">${label}</span>
        <span style="color:${color}">${display}</span>
      </div>
      <div class="score-bar-track">
        <div class="score-bar-fill" style="width:${pct}%;background:${color}88;background:linear-gradient(90deg,${color}44,${color})"></div>
      </div>
    </div>`;
}

// ── Decision Flow Diagram ─────────────────────────────────────────
function renderFlow(data) {
  const nodes = [
    { label: 'Image Analysis', active: true },
    { label: data.image_status, active: true },
    { label: 'ML Risk', active: true },
    { label: data.risk_level, active: true },
    { label: data.action.replace('_', ' '), active: true, final: true },
  ];

  document.getElementById('flowDiagram').innerHTML = nodes.map((n, i) => `
    ${i > 0 ? '<span class="flow-arrow">→</span>' : ''}
    <div class="flow-node ${n.active ? 'active-node' : ''} ${n.final ? 'final-node' : ''}">${n.label}</div>
  `).join('');
}

// ── Helpers ───────────────────────────────────────────────────────
function show(id) { document.getElementById(id)?.classList.remove('hidden'); }
function hide(id) { document.getElementById(id)?.classList.add('hidden'); }
