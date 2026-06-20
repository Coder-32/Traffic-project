/**
 * TrafficSense — Live Incident Command Map
 * Engine: Incident pins, jam circles, alternate routes, officer/barricade markers,
 *         sidebar panels, prediction alerts, and simulation loop.
 */

'use strict';

// ═══════════════════════════════════════════════════════════════
// 1.  DATA STORE
// ═══════════════════════════════════════════════════════════════

const INCIDENT_TYPES = {
  waterlogging:      { label: 'Waterlogging',        icon: '💧' },
  political_rally:   { label: 'Political Rally',      icon: '📢' },
  tree_fall:         { label: 'Tree Fall',            icon: '🌳' },
  vehicle_breakdown: { label: 'Vehicle Breakdown',    icon: '🔧' },
  accident:          { label: 'Accident',             icon: '⚡' },
  construction:      { label: 'Construction',         icon: '🚧' },
  festival:          { label: 'Festival / Procession',icon: '🎊' },
};

const incidents = [
  {
    id: 'inc_silkboard',
    type: 'waterlogging',
    name: 'Silk Board Junction',
    address: 'Silk Board Flyover, Hosur Road',
    cause: 'Heavy overnight rainfall; underpass flooded 0.4m',
    severity: 'high',
    x: 452, y: 444,
    jamKm: 2.5,         // predicted jam radius in km
    llmScore: 1.0,      // LLM severity multiplier (0–1)
    duration: 48,       // predicted jam duration in minutes
    officersNeeded: 4,
    active: true,
  },
  {
    id: 'inc_majestic',
    type: 'political_rally',
    name: 'KSR Bus Stand, Majestic',
    address: 'Majestic — Gubbi Thotadappa Rd',
    cause: 'Party election rally; route blocked 09:00–14:00',
    severity: 'high',
    x: 260, y: 232,
    jamKm: 2.2,
    llmScore: 0.95,
    duration: 120,
    officersNeeded: 6,
    active: true,
  },
  {
    id: 'inc_indiranagar',
    type: 'tree_fall',
    name: '100ft Road, Indiranagar',
    address: 'Indiranagar 100ft Road, Jyoti Nivas Circle',
    cause: 'Large tree fell post-storm; left lane blocked',
    severity: 'medium',
    x: 515, y: 212,
    jamKm: 1.4,
    llmScore: 0.65,
    duration: 25,
    officersNeeded: 2,
    active: true,
  },
  {
    id: 'inc_koramangala',
    type: 'vehicle_breakdown',
    name: 'Sony World Signal, Koramangala',
    address: 'Koramangala 80ft Road, Sony World Junction',
    cause: 'BMTC bus engine failure; 2 lanes blocked',
    severity: 'medium',
    x: 452, y: 335,
    jamKm: 1.2,
    llmScore: 0.6,
    duration: 18,
    officersNeeded: 2,
    active: true,
  },
  {
    id: 'inc_hebbal',
    type: 'accident',
    name: 'Hebbal Flyover (NH-44)',
    address: 'NH-44 Hebbal Elevated Expressway, Ramp 2',
    cause: 'Multi-vehicle collision — 3 vehicles, crane deployed',
    severity: 'high',
    x: 408, y: 72,
    jamKm: 2.0,
    llmScore: 0.88,
    duration: 35,
    officersNeeded: 5,
    active: true,
  },
  {
    id: 'inc_whitefield',
    type: 'construction',
    name: 'ITPL Main Road, Whitefield',
    address: 'ITPL Exit Gate — Whitefield Main Road',
    cause: 'Metro Phase 3 utility trenching; single lane active',
    severity: 'low',
    x: 730, y: 192,
    jamKm: 0.9,
    llmScore: 0.3,
    duration: 180,
    officersNeeded: 1,
    active: true,
  },
  {
    id: 'inc_jpnagar',
    type: 'festival',
    name: 'JP Nagar 7th Phase',
    address: 'JP Nagar 24th Main Road, near Gottigere',
    cause: 'Annual Ganesha procession; road closed 18:00–22:00',
    severity: 'medium',
    x: 262, y: 450,
    jamKm: 1.5,
    llmScore: 0.7,
    duration: 90,
    officersNeeded: 3,
    active: true,
  },
];

const officers = [
  { id: 'off_14', number: 14, x: 472, y: 458 },
  { id: 'off_7',  number: 7,  x: 244, y: 248 },
  { id: 'off_23', number: 23, x: 532, y: 228 },
  { id: 'off_5',  number: 5,  x: 392, y: 82  },
  { id: 'off_31', number: 31, x: 470, y: 348 },
];

const barricades = [
  { id: 'bar_1', x: 440, y: 418, angle: 30 },
  { id: 'bar_2', x: 248, y: 208, angle: 5  },
  { id: 'bar_3', x: 388, y: 60,  angle: 50 },
  { id: 'bar_4', x: 472, y: 60,  angle: 50 },
];

// Alternate routes — SVG path strings routed around jam circles
const alternateRoutes = [
  {
    id: 'alt_silkboard',
    // Silk Board bypass: goes east via HSR → Sarjapur Rd → ORR → Marathahalli
    path: 'M 490 558 Q 530 540 568 508 Q 610 468 640 420 Q 660 378 652 300',
    label: 'Hosur Rd Bypass via Sarjapur & ORR',
  },
  {
    id: 'alt_majestic',
    // Majestic bypass: curves south of jam, uses Residency Rd → MG Road
    path: 'M 248 90 Q 285 108 318 148 Q 350 188 380 218 Q 408 236 460 248',
    label: 'Inner Ring Road Bypass via Residency Rd',
  },
  {
    id: 'alt_hebbal',
    // Hebbal bypass: eastern ORR arc through Nagawara → Kalyan Nagar
    path: 'M 362 60 Q 418 45 488 65 Q 548 88 595 138 Q 628 178 652 240',
    label: 'Bellary Road Alt via Nagawara ORR Arc',
  },
];

// Prediction alert messages
const ALERTS = [
  { junction: 'Silk Board Junction', mins: 14, cause: 'spillover from waterlogging' },
  { junction: 'Hebbal Flyover', mins: 8,  cause: 'cascade from accident on NH-44' },
  { junction: 'Indiranagar 100ft Road', mins: 22, cause: 'tree-fall debris clearance delay' },
  { junction: 'MG Road / Brigade Junction', mins: 18, cause: 'political rally diversion overflow' },
  { junction: 'Koramangala 80ft Road', mins: 11, cause: 'BMTC breakdown queue buildup' },
];

// Forecast data (simulated NGBoost output, updates every cycle)
let forecastData = [
  { label: 'Now',  pct: 88, cls: 'crit' },
  { label: '+1h',  pct: 72, cls: 'mod'  },
  { label: '+2h',  pct: 55, cls: 'mod'  },
  { label: '+3h',  pct: 38, cls: 'low'  },
];

// ═══════════════════════════════════════════════════════════════
// 2.  STATE
// ═══════════════════════════════════════════════════════════════

let selectedId   = null;
let alertIndex   = 0;
const MAP_SCALE  = 56; // px per km in SVG coordinate space

// ═══════════════════════════════════════════════════════════════
// 3.  UTILITY
// ═══════════════════════════════════════════════════════════════

function sevColor(sev) {
  if (sev === 'high')   return '#f85149';
  if (sev === 'medium') return '#e3b341';
  return '#3fb950';
}

function jamPxRadius(inc) {
  // radius = km × llmScore × mapScale (NGBoost output × LLM severity score)
  return Math.round(inc.jamKm * inc.llmScore * MAP_SCALE);
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ═══════════════════════════════════════════════════════════════
// 4.  JAM RADIUS CIRCLES
// ═══════════════════════════════════════════════════════════════

function renderJamCircles() {
  const g = document.getElementById('lmJamCircles');
  if (!g) return;
  let html = '';
  incidents.forEach(inc => {
    if (!inc.active) return;
    const r = jamPxRadius(inc);
    const c = sevColor(inc.severity);
    const opacity = inc.severity === 'high' ? 0.18 : 0.12;
    const isSelected = selectedId === inc.id;
    const animAttr = (inc.severity === 'high')
      ? 'style="animation: jam-breathe 2.5s infinite ease-in-out;"'
      : '';

    html += `
      <g class="jam-circle" id="jam_${inc.id}">
        <!-- Outer glow ring (critical only) -->
        ${inc.severity === 'high' ? `
          <circle cx="${inc.x}" cy="${inc.y}" r="${r + 18}"
            fill="none" stroke="${c}" stroke-width="0.8" opacity="0.18"
            style="animation: jam-breathe 3s infinite ease-in-out 0.5s;"/>
        ` : ''}
        <!-- Main jam fill circle -->
        <circle cx="${inc.x}" cy="${inc.y}" r="${r}"
          fill="${c}" opacity="${isSelected ? opacity * 1.6 : opacity}"
          stroke="${c}" stroke-width="0.5"
          ${animAttr}/>
        <!-- Radius label -->
        <text x="${inc.x}" y="${inc.y + r - 6}"
          text-anchor="middle" font-size="8.5"
          font-family="Inter,sans-serif" font-weight="600"
          fill="${c}" opacity="0.7">${inc.jamKm} km jam</text>
      </g>`;
  });
  g.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
// 5.  ALTERNATE ROUTE POLYLINES
// ═══════════════════════════════════════════════════════════════

function renderAltRoutes() {
  const g = document.getElementById('lmAltRoutes');
  if (!g) return;
  let html = '';
  alternateRoutes.forEach((route, idx) => {
    const delay = (idx * 4) + 's';
    html += `
      <g id="route_${route.id}">
        <!-- Soft glow shadow pass -->
        <path d="${route.path}"
          fill="none" stroke="rgba(255,255,255,0.12)"
          stroke-width="8" stroke-linecap="round"/>
        <!-- Animated dashed white route -->
        <path d="${route.path}"
          class="alt-route-path"
          style="animation-delay: ${delay};"/>
        <!-- Arrow-like termination dot at end would require JS getBBox; skip for now -->
      </g>`;
  });
  g.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
// 6.  INCIDENT PINS
// ═══════════════════════════════════════════════════════════════

// Teardrop SVG path: origin at (0,0), tip at bottom, body above
const PIN_PATH = 'M 0,-22 C -12,-22 -16,-13 -16,-7 C -16,3 0,16 0,16 C 0,16 16,3 16,-7 C 16,-13 12,-22 0,-22 Z';

function renderPins() {
  const g = document.getElementById('lmPins');
  if (!g) return;
  let html = '';

  incidents.forEach(inc => {
    if (!inc.active) return;
    const c = sevColor(inc.severity);
    const isSelected = selectedId === inc.id;
    const scale = isSelected ? 1.25 : 1;
    const typeInfo = INCIDENT_TYPES[inc.type] || { icon: '?', label: inc.type };

    html += `
      <g class="incident-pin${isSelected ? ' selected' : ''}"
         id="pin_${inc.id}"
         transform="translate(${inc.x},${inc.y}) scale(${scale})"
         onclick="selectIncident('${inc.id}')"
         onmouseenter="showTooltip(event,'${inc.id}')"
         onmouseleave="hideTooltip()">

        ${isSelected ? `
          <!-- Expanding pulse ring for selected pin -->
          <circle r="22" fill="none" stroke="${c}" stroke-width="1.2" opacity="0.5"
            style="animation: pin-ring-expand 1.8s infinite ease-out;"/>
        ` : ''}

        <!-- Pin body -->
        <path class="pin-body" d="${PIN_PATH}"
          fill="${c}"
          opacity="${isSelected ? 1 : 0.9}"
          ${isSelected ? `filter="url(#redGlow)"` : ''}/>

        <!-- Icon inner circle -->
        <circle cx="0" cy="-8" r="10.5" fill="rgba(0,0,0,0.28)"/>

        <!-- Event type emoji icon -->
        <text x="0" y="-5"
          text-anchor="middle"
          dominant-baseline="central"
          font-size="11"
          style="user-select:none; pointer-events:none;">${typeInfo.icon}</text>

      </g>`;
  });

  g.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
// 7.  OFFICER MARKERS
// ═══════════════════════════════════════════════════════════════

function renderOfficers() {
  const g = document.getElementById('lmOfficers');
  if (!g) return;
  let html = '';
  officers.forEach((off, i) => {
    const delay = (i * 0.4) + 's';
    html += `
      <g class="officer-marker" id="off_${off.id}"
         title="Officer #${off.number}"
         filter="url(#greenGlow)">
        <!-- Outer ring -->
        <circle cx="${off.x}" cy="${off.y}" r="12"
          fill="rgba(63,185,80,0.15)"
          stroke="#3fb950" stroke-width="1.2"
          opacity="0.7"/>
        <!-- Main circle -->
        <circle cx="${off.x}" cy="${off.y}" r="9"
          fill="#3fb950"
          class="officer-marker-circle"
          style="animation-delay: ${delay};"/>
        <!-- Badge number -->
        <text x="${off.x}" y="${off.y}"
          text-anchor="middle" dominant-baseline="central"
          font-size="7" font-weight="700"
          fill="#000" style="pointer-events:none; user-select:none;">${off.number}</text>
      </g>`;
  });
  g.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
// 8.  BARRICADE MARKERS
// ═══════════════════════════════════════════════════════════════

function renderBarricades() {
  const g = document.getElementById('lmBarricades');
  if (!g) return;
  let html = '';
  barricades.forEach(bar => {
    html += `
      <g transform="translate(${bar.x},${bar.y}) rotate(${bar.angle})">
        <!-- Glow -->
        <rect x="-9" y="-4.5" width="18" height="9" rx="1.5"
          fill="#f85149" opacity="0.18"/>
        <!-- Main barricade body (red rectangle) -->
        <rect x="-8" y="-4" width="16" height="8" rx="1.5"
          fill="#f85149" opacity="0.9"/>
        <!-- Diagonal stripe lines -->
        <line x1="-6" y1="-4" x2="-2" y2="4"  stroke="#0d1117" stroke-width="1.5" opacity="0.5"/>
        <line x1="-1" y1="-4" x2="3"  y2="4"  stroke="#0d1117" stroke-width="1.5" opacity="0.5"/>
        <line x1="4"  y1="-4" x2="8"  y2="4"  stroke="#0d1117" stroke-width="1.5" opacity="0.5"/>
      </g>`;
  });
  g.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
// 9.  INCIDENT CARD LIST (Sidebar Panel 1)
// ═══════════════════════════════════════════════════════════════

function renderIncidentList() {
  const el = document.getElementById('lmIncidentList');
  if (!el) return;
  let html = '';

  incidents.forEach(inc => {
    if (!inc.active) return;
    const c = sevColor(inc.severity);
    const typeInfo = INCIDENT_TYPES[inc.type] || { icon: '?', label: inc.type };
    const isSelected = selectedId === inc.id;
    const r = jamPxRadius(inc);

    html += `
      <div class="lm-card sev-${inc.severity}${isSelected ? ' active' : ''}"
           id="card_${inc.id}"
           onclick="selectIncident('${inc.id}')">
        <div class="lm-card-icon sev-${inc.severity}">${typeInfo.icon}</div>
        <div class="lm-card-body">
          <div class="lm-card-top">
            <span class="lm-card-name">${escHtml(inc.name)}</span>
            <span class="sev-badge ${inc.severity}">${inc.severity}</span>
          </div>
          <div class="lm-card-cause">${escHtml(inc.cause)}</div>
          <div class="lm-card-meta">
            <span class="lm-meta">⏱ <strong>${inc.duration} min</strong></span>
            <span class="lm-meta">👮 <strong>${inc.officersNeeded}</strong>&nbsp;officers</span>
            <span class="lm-meta">📍 <strong>${inc.jamKm} km</strong>&nbsp;jam</span>
          </div>
        </div>
      </div>`;
  });

  el.innerHTML = html;

  // Update badge count
  const badge = document.getElementById('incidentCountBadge');
  if (badge) badge.textContent = `${incidents.filter(i => i.active).length} Active`;
}

// ═══════════════════════════════════════════════════════════════
// 10. CONGESTION FORECAST BARS (Panel 2)
// ═══════════════════════════════════════════════════════════════

function renderForecast() {
  const el = document.getElementById('lmForecastBody');
  if (!el) return;
  let html = '';
  forecastData.forEach(row => {
    html += `
      <div class="fc-row">
        <span class="fc-label">${escHtml(row.label)}</span>
        <div class="fc-track">
          <div class="fc-fill ${row.cls}" style="width:${row.pct}%;"></div>
        </div>
        <span class="fc-val ${row.cls}">${row.pct}%</span>
      </div>`;
  });
  el.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════════
// 11. DEPLOYMENT SUMMARY METRICS (Panel 3)
// ═══════════════════════════════════════════════════════════════

function renderDeployment() {
  const totalOfficers   = incidents.reduce((s, i) => i.active ? s + i.officersNeeded : s, 0);
  const totalBarricades = barricades.length + Math.floor(incidents.filter(i => i.active && i.severity === 'high').length * 1.5);
  const totalRoutes     = alternateRoutes.length;

  const setEl = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
  setEl('metOfficers',  totalOfficers);
  setEl('metBarricades', totalBarricades);
  setEl('metRoutes',    totalRoutes);
}

// ═══════════════════════════════════════════════════════════════
// 12. CITY SNAPSHOT (Panel 4)
// ═══════════════════════════════════════════════════════════════

function renderSnapshot() {
  const activeCount  = incidents.filter(i => i.active).length;
  const criticalCount = incidents.filter(i => i.active && i.severity === 'high').length;
  const offCount     = officers.length;
  const estPeople    = (incidents.filter(i => i.active)
    .reduce((s, i) => s + Math.round(i.jamKm * i.llmScore * 1800), 0));

  const now  = new Date();
  const hour = now.getHours();
  // simple peak hour logic
  const peakLabel = (hour >= 8 && hour < 11) ? '09:00 – 11:00'
    : (hour >= 17 && hour < 20) ? '17:00 – 20:00'
    : (hour >= 7 && hour < 23)  ? `${String(hour).padStart(2,'0')}:00 – ${String(hour+2).padStart(2,'0')}:00`
    : 'Off-peak';

  const setEl = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
  const setHtml = (id, val) => { const e = document.getElementById(id); if (e) e.innerHTML = val; };

  setEl('snapIncidents', activeCount);
  setHtml('snapIncidentsSub', `<span style="color:#f85149;">${criticalCount} critical</span>`);
  setEl('snapOfficers',  offCount);
  setHtml('snapOfficersSub', `<span style="color:#58a6ff;">${offCount} deployed</span>`);
  setEl('snapPeople',    estPeople.toLocaleString('en-IN'));
  setEl('snapPeakHour',  peakLabel);
  setHtml('snapPeakSub', `<span style="color:#8b949e;">today's load peak</span>`);
}

// ═══════════════════════════════════════════════════════════════
// 13. PREDICTION ALERT BANNER
// ═══════════════════════════════════════════════════════════════

function updateAlert() {
  const a = ALERTS[alertIndex % ALERTS.length];
  alertIndex++;
  const el = document.getElementById('alertText');
  if (!el) return;
  el.innerHTML = `<strong>High congestion</strong> predicted near <strong>${escHtml(a.junction)}</strong>
    in <strong>${a.mins} minutes</strong> — ${escHtml(a.cause)}.`;
}

// ═══════════════════════════════════════════════════════════════
// 14. INCIDENT SELECTION (cross-highlight pin ↔ card)
// ═══════════════════════════════════════════════════════════════

window.selectIncident = function(id) {
  selectedId = (selectedId === id) ? null : id;   // toggle
  renderPins();
  renderJamCircles();
  renderIncidentList();

  // Scroll selected card into view
  if (selectedId) {
    const card = document.getElementById(`card_${selectedId}`);
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
};

// ═══════════════════════════════════════════════════════════════
// 15. TOOLTIP
// ═══════════════════════════════════════════════════════════════

window.showTooltip = function(evt, id) {
  const inc = incidents.find(i => i.id === id);
  if (!inc) return;
  const typeInfo = INCIDENT_TYPES[inc.type] || { label: inc.type };
  const tt = document.getElementById('lmTooltip');
  if (!tt) return;

  document.getElementById('ttName').textContent    = inc.name;
  const ttSev = document.getElementById('ttSev');
  ttSev.textContent  = inc.severity.toUpperCase();
  ttSev.className    = `tt-sev ${inc.severity}`;
  document.getElementById('ttType').textContent     = typeInfo.label;
  document.getElementById('ttCause').textContent    = inc.cause;
  document.getElementById('ttRadius').textContent   = `${inc.jamKm} km (LLM score: ${inc.llmScore})`;
  document.getElementById('ttDuration').textContent = `~${inc.duration} min`;
  document.getElementById('ttOfficers').textContent = `${inc.officersNeeded} officers`;

  tt.style.display = 'block';
  moveTt(evt);
};

window.hideTooltip = function() {
  const tt = document.getElementById('lmTooltip');
  if (tt) tt.style.display = 'none';
};

function moveTt(evt) {
  const tt = document.getElementById('lmTooltip');
  if (!tt || tt.style.display === 'none') return;
  const x = evt.clientX + 14;
  const y = evt.clientY - 28;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  tt.style.left = Math.min(x, vw - tt.offsetWidth - 12) + 'px';
  tt.style.top  = Math.max(8, Math.min(y, vh - tt.offsetHeight - 12)) + 'px';
}

document.addEventListener('mousemove', moveTt);

// ═══════════════════════════════════════════════════════════════
// 16. SIDEBAR TOGGLE
// ═══════════════════════════════════════════════════════════════

function initSidebarToggle() {
  const btn    = document.getElementById('lmSidebarToggle');
  const layout = document.getElementById('lmLayout');
  if (!btn || !layout) return;

  btn.addEventListener('click', () => {
    const collapsed = layout.classList.toggle('collapsed');
    btn.textContent = collapsed ? '‹' : '›';
    btn.title = collapsed ? 'Expand Sidebar' : 'Collapse Sidebar';
  });
}

// ═══════════════════════════════════════════════════════════════
// 17. LIVE SIMULATION LOOP
// ═══════════════════════════════════════════════════════════════

function runSimulation() {
  setInterval(() => {
    // Slightly mutate forecast values
    forecastData = forecastData.map((row, i) => {
      const delta = (Math.random() * 8 - 4);
      const newPct = Math.max(10, Math.min(98, row.pct + delta));
      const cls = newPct >= 75 ? 'crit' : newPct >= 45 ? 'mod' : 'low';
      return { ...row, pct: Math.round(newPct), cls };
    });

    // Slightly mutate some jam radii
    incidents.forEach(inc => {
      const drift = (Math.random() * 0.2 - 0.1);
      inc.jamKm = Math.max(0.5, Math.min(3.5, inc.jamKm + drift));
    });

    // Re-render dynamic layers
    renderJamCircles();
    renderPins();
    renderForecast();
    renderDeployment();
    renderSnapshot();
    renderIncidentList();
  }, 5000);

  // Prediction banner cycles every 18s
  setInterval(updateAlert, 18000);
}

// ═══════════════════════════════════════════════════════════════
// 18. BOOTSTRAP
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  renderJamCircles();
  renderAltRoutes();
  renderBarricades();
  renderOfficers();
  renderPins();
  renderIncidentList();
  renderForecast();
  renderDeployment();
  renderSnapshot();
  updateAlert();
  initSidebarToggle();
  runSimulation();
});
