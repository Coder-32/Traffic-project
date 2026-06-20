/**
 * TrafficSense - Bengaluru Traffic Operations Control Logic
 * Core Engine: Live Data Simulation, Dynamic SVG Map, Deployment System, and Canvas Analytics
 */

document.addEventListener('DOMContentLoaded', () => {
  
  // ==========================================
  // 1. DATA DEFINITIONS & STATE
  // ==========================================
  
  const junctions = {
    hebbal: { id: 'hebbal', name: 'Hebbal Flyover', x: 380, y: 70, baseSpeed: 50, currentSpeed: 42, incidentCount: 0 },
    yeswanthpur: { id: 'yeswanthpur', name: 'Yeswanthpur Junction', x: 180, y: 120, baseSpeed: 40, currentSpeed: 38, incidentCount: 0 },
    majestic: { id: 'majestic', name: 'Majestic Central', x: 240, y: 220, baseSpeed: 25, currentSpeed: 12, incidentCount: 1 },
    jayanagar: { id: 'jayanagar', name: 'Jayanagar 4th Block', x: 280, y: 380, baseSpeed: 30, currentSpeed: 28, incidentCount: 0 },
    silkboard: { id: 'silkboard', name: 'Silk Board Junction', x: 440, y: 410, baseSpeed: 18, currentSpeed: 8, incidentCount: 1 },
    koramangala: { id: 'koramangala', name: 'Koramangala 80ft Rd', x: 450, y: 310, baseSpeed: 28, currentSpeed: 18, incidentCount: 1 },
    indiranagar: { id: 'indiranagar', name: 'Indiranagar 100ft Rd', x: 540, y: 200, baseSpeed: 32, currentSpeed: 14, incidentCount: 0 },
    whitefield: { id: 'whitefield', name: 'Whitefield ITPL', x: 700, y: 160, baseSpeed: 35, currentSpeed: 32, incidentCount: 0 },
    orr: { id: 'orr', name: 'Outer Ring Road (Marathahalli)', x: 600, y: 300, baseSpeed: 45, currentSpeed: 24, incidentCount: 0 },
    ecity: { id: 'ecity', name: 'Electronic City Phase 1', x: 620, y: 450, baseSpeed: 55, currentSpeed: 50, incidentCount: 0 }
  };

  const corridors = [
    { from: 'hebbal', to: 'yeswanthpur' },
    { from: 'yeswanthpur', to: 'majestic' },
    { from: 'majestic', to: 'jayanagar' },
    { from: 'jayanagar', to: 'silkboard' },
    { from: 'silkboard', to: 'ecity' },
    { from: 'silkboard', to: 'koramangala' },
    { from: 'koramangala', to: 'indiranagar' },
    { from: 'indiranagar', to: 'whitefield' },
    { from: 'whitefield', to: 'orr' },
    { from: 'orr', to: 'silkboard' },
    { from: 'hebbal', to: 'indiranagar' },
    { from: 'majestic', to: 'koramangala' }
  ];

  let incidents = [
    { id: 'inc_1', junctionId: 'silkboard', title: 'Water Logging at Underpass', severity: 'critical', desc: 'Severe water collection causing vehicles to crawl. Alternate route advised.', time: '12:05 PM', active: true },
    { id: 'inc_2', junctionId: 'majestic', title: 'BMTC Bus Breakdown', severity: 'critical', desc: 'Disabled bus blocking left lane towards railway station. Crane dispatched.', time: '12:12 PM', active: true },
    { id: 'inc_3', junctionId: 'koramangala', title: 'Slow Traffic Clearance', severity: 'moderate', desc: 'High volume tailback heading to Sony World signal. Normal peak loads.', time: '12:18 PM', active: true }
  ];

  let officers = [
    { id: 'off_1', name: 'Inspector R. Kumar', junctionId: 'silkboard', status: 'on-scene', time: '12:08 PM' },
    { id: 'off_2', name: 'Sub-Inspector S. Murthy', junctionId: 'majestic', status: 'on-scene', time: '12:15 PM' },
    { id: 'off_3', name: 'Warden P. Patil', junctionId: 'koramangala', status: 'patrolling', time: '11:45 AM' },
    { id: 'off_4', name: 'Inspector A. Gowda', junctionId: 'indiranagar', status: 'patrolling', time: '12:02 PM' }
  ];

  const forecasts = [
    {
      id: 'fc_ipl',
      title: 'IPL T20 Cricket Match (Chinnaswamy Stadium)',
      date: 'Today, 4:00 PM — 11:30 PM',
      impact: 'high',
      areas: ['Majestic', 'Hebbal', 'Indiranagar'],
      mitigation: 'Deploy extra officers around MG Road/Cubbon Park. Route North-bound vehicles via ORR bypass.',
      triggered: false
    },
    {
      id: 'fc_rally',
      title: 'Political Assembly & Rally (Vidhana Soudha)',
      date: 'Tomorrow, 9:00 AM — 2:00 PM',
      impact: 'high',
      areas: ['Majestic', 'Jayanagar'],
      mitigation: 'Implement one-way routing around Raj Bhavan. Enforce alternate transit routes via outer circles.',
      triggered: false
    },
    {
      id: 'fc_monsoon',
      title: 'IMD Monsoon Red Alert Forecast',
      date: 'Today, 2:30 PM onwards',
      impact: 'high',
      areas: ['Silk Board', 'Outer Ring Road', 'Koramangala'],
      mitigation: 'Pre-position pumping equipment and alert water rescue forces. Divert ORR traffic to Service Road systems.',
      triggered: false
    },
    {
      id: 'fc_techpark',
      title: 'IT Corridor Peak Exit Shift (Whitefield)',
      date: 'Friday, 5:00 PM — 8:00 PM',
      impact: 'medium',
      areas: ['Whitefield', 'Outer Ring Road'],
      mitigation: 'Stagger exit timings with IT units. Synchronize traffic signals for 180s green wave along ITPL Main Road.',
      triggered: false
    }
  ];

  // Map Active Selection State
  let selectedJunctionId = null;
  let activeSeverityFilter = 'all';

  // ==========================================
  // 2. INITIALIZATION & LIVE CLOCK
  // ==========================================

  function initClock() {
    const clockEl = document.getElementById('liveClock');
    setInterval(() => {
      const now = new Date();
      clockEl.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
    }, 1000);
  }

  // ==========================================
  // 3. TAB CONTROLLER
  // ==========================================

  function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');

        // Deactivate all
        tabButtons.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));

        // Activate selected
        btn.classList.add('active');
        
        let viewId = '';
        if (targetTab === 'liveMap') viewId = 'viewLiveMap';
        else if (targetTab === 'eventForecast') viewId = 'viewEventForecast';
        else if (targetTab === 'deploymentPlan') viewId = 'viewDeploymentPlan';
        else if (targetTab === 'analytics') viewId = 'viewAnalytics';

        const contentEl = document.getElementById(viewId);
        if (contentEl) {
          contentEl.classList.add('active');
        }

        // Render analytics if tab matches
        if (targetTab === 'analytics') {
          renderAnalyticsCharts();
        }
      });
    });
  }

  // ==========================================
  // 4. MAP RENDER ENGINE (SVG)
  // ==========================================

  function getSpeedColor(speed, baseSpeed) {
    const ratio = speed / baseSpeed;
    if (ratio < 0.45 || speed < 15) return '#f85149'; // Red (High severity / critical)
    if (ratio < 0.75 || speed < 30) return '#e3b341'; // Amber (Medium severity / moderate)
    return '#3fb950'; // Green (Low severity / clear)
  }

  function renderMap() {
    const linksGroup = document.getElementById('mapLinks');
    const nodesGroup = document.getElementById('mapNodes');
    const incidentsGroup = document.getElementById('mapIncidents');
    const officersGroup = document.getElementById('mapOfficers');

    // 1. Render Corridors (Links)
    let linksHtml = '';
    corridors.forEach(corr => {
      const fromJ = junctions[corr.from];
      const toJ = junctions[corr.to];
      if (fromJ && toJ) {
        // Average speed represents congestion
        const avgSpeed = (fromJ.currentSpeed + toJ.currentSpeed) / 2;
        const avgBaseSpeed = (fromJ.baseSpeed + toJ.baseSpeed) / 2;
        const color = getSpeedColor(avgSpeed, avgBaseSpeed);
        
        let strokeClass = 'low-congestion';
        if (color === '#f85149') strokeClass = 'high-congestion';
        else if (color === '#e3b341') strokeClass = 'medium-congestion';

        const isHighlighted = (selectedJunctionId === corr.from || selectedJunctionId === corr.to) ? ' highlighted' : '';

        linksHtml += `<line class="map-link ${strokeClass}${isHighlighted}" 
          x1="${fromJ.x}" y1="${fromJ.y}" 
          x2="${toJ.x}" y2="${toJ.y}" 
          stroke="${color}" />`;
      }
    });
    linksGroup.innerHTML = linksHtml;

    // 2. Render Junctions (Nodes)
    let nodesHtml = '';
    Object.values(junctions).forEach(j => {
      const color = getSpeedColor(j.currentSpeed, j.baseSpeed);
      let statusClass = 'congested-green';
      if (color === '#f85149') statusClass = 'congested-red';
      else if (color === '#e3b341') statusClass = 'congested-amber';

      const selectedBorder = selectedJunctionId === j.id
        ? 'stroke="#58a6ff" stroke-width="3"'
        : '';

      nodesHtml += `
        <g class="map-node ${statusClass}" id="node_${j.id}" transform="translate(${j.x}, ${j.y})"
           onclick="selectJunction('${j.id}')"
           onmouseenter="showTooltip(event, '${j.id}')"
           onmouseleave="hideTooltip()">
          <!-- Outer border circle -->
          <circle class="map-node-circle" r="14" ${selectedBorder} />
          <!-- Speed label index inside -->
          <text fill="#e6edf3" font-size="8" font-weight="700" text-anchor="middle" y="3">${j.currentSpeed}</text>
          
          <!-- Label backdrop -->
          <rect x="-35" y="-28" width="70" height="12" fill="#0c0e12" opacity="0.85" rx="3" ry="3" />
          <text class="map-node-label" y="-20">${j.name.split(' ')[0]}</text>
        </g>
      `;
    });
    nodesGroup.innerHTML = nodesHtml;

    // 3. Render Incident Highlights (Pulsing Red indicators)
    let incidentsHtml = '';
    incidents.forEach(inc => {
      if (inc.active) {
        const j = junctions[inc.junctionId];
        if (j) {
          incidentsHtml += `
            <g transform="translate(${j.x}, ${j.y - 12})">
              <circle class="map-incident-glow" r="10" />
              <polygon points="0,-7 6,4 -6,4" fill="#f85149" stroke="#0d1117" stroke-width="0.5" />
            </g>
          `;
        }
      }
    });
    incidentsGroup.innerHTML = incidentsHtml;

    // 4. Render Officers (Blue markers)
    let officersHtml = '';
    // Count officers per junction to offset overlapping markers
    const jCounts = {};
    officers.forEach(off => {
      const j = junctions[off.junctionId];
      if (j) {
        if (!jCounts[off.junctionId]) jCounts[off.junctionId] = 0;
        jCounts[off.junctionId]++;
        
        // Offset multiple officers slightly
        const offset = (jCounts[off.junctionId] - 1) * 8;
        officersHtml += `
          <circle class="map-officer-marker" cx="${j.x + 12 + offset}" cy="${j.y + 12}" r="5" title="${off.name}" />
        `;
      }
    });
    officersGroup.innerHTML = officersHtml;
  }

  window.selectJunction = function(id) {
    selectedJunctionId = id;
    renderMap();
    updateJunctionInspector(id);
  };

  window.showTooltip = function(event, id) {
    const j = junctions[id];
    if (!j) return;
    const tooltip = document.getElementById('mapTooltip');
    const nameEl = document.getElementById('tooltipName');
    const speedEl = document.getElementById('tooltipSpeed');
    const color = getSpeedColor(j.currentSpeed, j.baseSpeed);
    const status = color === '#f85149' ? 'CRITICAL' : color === '#e3b341' ? 'MODERATE' : 'CLEAR';
    nameEl.textContent = j.name;
    speedEl.textContent = `${j.currentSpeed} km/h — ${status}`;
    speedEl.style.color = color;
    tooltip.style.display = 'block';
  };

  window.hideTooltip = function() {
    const tooltip = document.getElementById('mapTooltip');
    if (tooltip) tooltip.style.display = 'none';
  };

  // Follow cursor
  document.getElementById('mapViewport')?.addEventListener('mousemove', (e) => {
    const tooltip = document.getElementById('mapTooltip');
    if (tooltip && tooltip.style.display === 'block') {
      const rect = e.currentTarget.getBoundingClientRect();
      tooltip.style.left = (e.clientX - rect.left + 14) + 'px';
      tooltip.style.top = (e.clientY - rect.top - 28) + 'px';
    }
  });

  // ==========================================
  // 5. SIDEBARS & DETAILS UPDATE
  // ==========================================

  function updateJunctionInspector(id) {
    const j = junctions[id];
    const nameEl = document.getElementById('inspectorJunctionName');
    const statusEl = document.getElementById('inspectorJunctionStatus');
    const speedEl = document.getElementById('inspectorJunctionSpeed');
    const statsEl = document.getElementById('inspectorJunctionStats');

    if (!j) return;

    nameEl.textContent = j.name;
    speedEl.textContent = `${j.currentSpeed} km/h`;

    const color = getSpeedColor(j.currentSpeed, j.baseSpeed);
    statusEl.className = 'severity-pill';
    
    if (color === '#f85149') {
      statusEl.classList.add('critical');
      statusEl.textContent = 'CRITICAL GRIDLOCK';
    } else if (color === '#e3b341') {
      statusEl.classList.add('moderate');
      statusEl.textContent = 'CONGESTED';
    } else {
      statusEl.classList.add('low');
      statusEl.textContent = 'CLEAR';
    }

    // Load active incident or general stats
    const jIncidents = incidents.filter(inc => inc.junctionId === id && inc.active);
    const jOfficers = officers.filter(off => off.junctionId === id);

    let infoHtml = `
      <div style="display:flex; justify-content:space-between;"><span>Baseline Limit:</span><span style="color:#e6edf3;">${j.baseSpeed} km/h</span></div>
      <div style="display:flex; justify-content:space-between;"><span>Active Incidents:</span><span style="color:${jIncidents.length > 0 ? 'var(--color-red)' : 'var(--color-green)'}; font-weight:600;">${jIncidents.length}</span></div>
      <div style="display:flex; justify-content:space-between;"><span>Deployed Officers:</span><span style="color:var(--color-blue); font-weight:600;">${jOfficers.length}</span></div>
    `;

    if (jIncidents.length > 0) {
      infoHtml += `
        <div style="border-top: 0.5px solid var(--border-color); margin-top: 6px; padding-top: 6px;">
          <span style="font-size:10px; font-weight:600; text-transform:uppercase; color:var(--color-red);">Incident Log:</span>
          <div style="color:var(--text-primary); font-weight:500; font-size:12px; margin-top: 2px;">${jIncidents[0].title}</div>
          <div style="font-size:11px; margin-top: 2px;">${jIncidents[0].desc}</div>
        </div>
      `;
    }

    statsEl.innerHTML = infoHtml;
  }

  function renderIncidentsList() {
    const listEl = document.getElementById('incidentsList');
    
    const filtered = incidents.filter(inc => {
      if (activeSeverityFilter === 'all') return true;
      if (activeSeverityFilter === 'critical') return inc.severity === 'critical';
      if (activeSeverityFilter === 'moderate') return inc.severity === 'moderate';
      if (activeSeverityFilter === 'clear') return inc.severity === 'low';
      return true;
    });

    let html = '';
    if (filtered.length === 0) {
      html = '<div style="color:var(--text-muted); font-size:12px; padding:12px; text-align:center;">No active incidents in this category.</div>';
    } else {
      filtered.forEach(inc => {
        const isSelected = selectedJunctionId === inc.junctionId ? ' active-selection' : '';
        const sevClass = inc.severity === 'critical' ? 'critical' : (inc.severity === 'moderate' ? 'moderate' : 'low');
        const j = junctions[inc.junctionId];
        
        html += `
          <div class="incident-card${isSelected}" onclick="selectJunction('${inc.junctionId}')">
            <div class="incident-meta">
              <span class="severity-pill ${sevClass}">${inc.severity}</span>
              <span class="incident-time">${inc.time}</span>
            </div>
            <div class="incident-title">${inc.title}</div>
            <div class="incident-desc">${j ? j.name : 'Unknown Location'} — ${inc.desc}</div>
          </div>
        `;
      });
    }

    listEl.innerHTML = html;
    
    // Update critical counts
    const criticalCount = incidents.filter(i => i.severity === 'critical' && i.active).length;
    document.getElementById('incidentCountBadge').textContent = `${criticalCount} CRITICAL`;
  }

  // ==========================================
  // 6. FILTER CONTROLS
  // ==========================================

  function initFilters() {
    const filters = [
      { id: 'filterAll', val: 'all' },
      { id: 'filterCritical', val: 'critical' },
      { id: 'filterModerate', val: 'moderate' },
      { id: 'filterClear', val: 'clear' }
    ];

    filters.forEach(f => {
      const btn = document.getElementById(f.id);
      if (btn) {
        btn.addEventListener('click', () => {
          filters.forEach(other => document.getElementById(other.id).classList.remove('active'));
          btn.classList.add('active');
          activeSeverityFilter = f.val;
          renderIncidentsList();
        });
      }
    });
  }

  // ==========================================
  // 7. EVENT FORECASTS CONTROLLER
  // ==========================================

  function renderForecasts() {
    const container = document.getElementById('forecastsContainer');
    let html = '';

    forecasts.forEach(fc => {
      const btnText = fc.triggered ? 'Mitigation Active' : 'Activate Mitigation';
      const btnClass = fc.triggered ? 'btn-trigger-plan triggered' : 'btn-trigger-plan';
      const impactClass = fc.impact === 'high' ? 'high' : 'medium';

      html += `
        <div class="forecast-card">
          <div class="forecast-header">
            <div>
              <div class="forecast-title">${fc.title}</div>
              <div class="forecast-date">${fc.date}</div>
            </div>
            <span class="forecast-impact-badge ${impactClass}">${fc.impact} impact</span>
          </div>
          
          <div class="forecast-details">
            <span style="font-weight:600; color:var(--text-primary);">Affected Zones:</span>
            <div class="forecast-affected-areas" style="margin-top: 4px;">
              ${fc.areas.map(a => `<span class="area-tag">${a}</span>`).join('')}
            </div>
          </div>
          
          <div>
            <div class="mitigation-header">OPERATIONAL PLAN</div>
            <ul class="mitigation-steps">
              ${fc.mitigation.split('. ').filter(s => s).map(s => `<li>${s}</li>`).join('')}
            </ul>
          </div>
          
          <button class="${btnClass}" onclick="toggleForecastMitigation('${fc.id}')">${btnText}</button>
        </div>
      `;
    });

    container.innerHTML = html;
  }

  window.toggleForecastMitigation = function(id) {
    const fc = forecasts.find(f => f.id === id);
    if (!fc) return;

    fc.triggered = !fc.triggered;
    
    // Perform simulated actions
    if (fc.triggered) {
      if (id === 'fc_ipl') {
        // Diversion route for Chinnaswamy: Silk board / Majestic to Indiranagar
        showAlternateRoute('majestic', 'indiranagar');
      } else if (id === 'fc_monsoon') {
        // Red alert Monsoon Silk Board bypass via ORR
        showAlternateRoute('orr', 'ecity');
      } else if (id === 'fc_rally') {
        showAlternateRoute('hebbal', 'indiranagar');
      }
    } else {
      hideAlternateRoute();
    }

    renderForecasts();
  };

  function showAlternateRoute(fromId, toId) {
    const fromJ = junctions[fromId];
    const toJ = junctions[toId];
    
    const altPath = document.getElementById('altRoutePath');
    const routePanel = document.getElementById('routeInfoPanel');
    const routeTitle = document.getElementById('routeTitle');
    const routeDetails = document.getElementById('routeDetails');
    const routeSavings = document.getElementById('routeSavings');

    if (fromJ && toJ && altPath) {
      // Draw alternate path on map
      // Draw bezier curves or straight lines
      const midX = (fromJ.x + toJ.x) / 2 + 50;
      const midY = (fromJ.y + toJ.y) / 2 - 50;
      
      altPath.setAttribute('d', `M ${fromJ.x} ${fromJ.y} Q ${midX} ${midY} ${toJ.x} ${toJ.y}`);
      altPath.style.display = 'block';

      // Update diversion UI
      routeTitle.textContent = `${fromJ.name.split(' ')[0]} to ${toJ.name.split(' ')[0]} Alternate`;
      routeDetails.textContent = `Live bypass generated via outer loop to relieve congestion corridor between ${fromJ.name.split(' ')[0]} and ${toJ.name.split(' ')[0]}.`;
      routeSavings.textContent = `Saving estimate: ~${Math.floor(Math.random() * 12) + 10} mins`;
      routePanel.style.display = 'flex';
    }
  }

  function hideAlternateRoute() {
    const altPath = document.getElementById('altRoutePath');
    const routePanel = document.getElementById('routeInfoPanel');
    if (altPath) altPath.style.display = 'none';
    if (routePanel) routePanel.style.display = 'none';
  }

  // ==========================================
  // 8. DEPLOYMENT PLAN CONTROLLER
  // ==========================================

  function renderDeployment() {
    const tableBody = document.getElementById('deploymentTableBody');
    let html = '';

    officers.forEach(off => {
      const j = junctions[off.junctionId];
      const jName = j ? j.name : 'Unassigned';
      
      let statusClass = 'patrolling';
      if (off.status === 'on-scene') statusClass = 'on-scene';
      else if (off.status === 'dispatched') statusClass = 'dispatched';

      const avatarInitials = off.name.split(' ').map(n => n.charAt(0)).join('');

      html += `
        <tr>
          <td>
            <div class="officer-badge">
              <div class="officer-avatar">${avatarInitials}</div>
              <div>
                <div style="font-weight:600;">${off.name}</div>
                <div style="font-size:10px; color:var(--text-muted);">Traffic Dept</div>
              </div>
            </div>
          </td>
          <td style="font-weight: 500;">${jName}</td>
          <td>
            <span class="status-indicator ${statusClass}">${off.status}</span>
          </td>
          <td style="color: var(--text-muted); font-variant-numeric: tabular-nums;">${off.time}</td>
          <td>
            <button class="btn-remove-officer" onclick="recallOfficer('${off.id}')" title="Recall Patrol">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </td>
        </tr>
      `;
    });

    tableBody.innerHTML = html;

    // Populate dispatch dropdown
    const junctionSelect = document.getElementById('officerJunction');
    if (junctionSelect && junctionSelect.children.length === 0) {
      let optionsHtml = '';
      Object.values(junctions).forEach(j => {
        optionsHtml += `<option value="${j.id}">${j.name}</option>`;
      });
      junctionSelect.innerHTML = optionsHtml;
    }

    // Update active badges
    document.getElementById('totalOfficersBadge').textContent = `${officers.length} Officers Active`;
    document.getElementById('activeOfficersValue').textContent = `${Math.round((officers.length / Object.keys(junctions).length) * 100)}%`;
    document.getElementById('activeOfficersTrend').textContent = `${officers.length} active deployments`;
  }

  window.recallOfficer = function(id) {
    officers = officers.filter(off => off.id !== id);
    renderDeployment();
    renderMap();
  };

  function initDispatchForm() {
    const form = document.getElementById('dispatchForm');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const nameInput = document.getElementById('officerName');
        const junctionSelect = document.getElementById('officerJunction');
        const statusSelect = document.getElementById('officerStatus');

        const now = new Date();
        const timestamp = now.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true
        });

        const newOfficer = {
          id: `off_${Date.now()}`,
          name: nameInput.value,
          junctionId: junctionSelect.value,
          status: statusSelect.value,
          time: timestamp
        };

        officers.push(newOfficer);
        
        // Reset form inputs
        nameInput.value = '';
        
        renderDeployment();
        renderMap();
      });
    }
  }

  // ==========================================
  // 9. CUSTOM ANALYTICS CHARTS (HTML5 Canvas 2D)
  // ==========================================

  function drawBarChart(canvasId, title, labels, data, barColor) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    // Support high DPI screens
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    
    const ctx = canvas.getContext('2d');
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    const width = rect.width;
    const height = rect.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Layout margins
    const padding = { top: 20, right: 20, bottom: 40, left: 45 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    // Grid colors
    const gridColor = '#21262d';
    const textColor = '#8b949e';
    
    // Find max value for scaling
    const maxVal = Math.max(...data) * 1.15 || 10;
    
    // Draw Y-Axis labels & horizontal gridlines
    const gridLines = 4;
    ctx.font = '10px Inter, sans-serif';
    ctx.fillStyle = textColor;
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 0.5;
    
    for (let i = 0; i <= gridLines; i++) {
      const val = (maxVal / gridLines) * i;
      const y = padding.top + chartHeight - (chartHeight / gridLines) * i;
      
      // Draw gridline
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      
      // Draw label
      ctx.fillText(Math.round(val), padding.left - 12, y + 3);
    }
    
    // Draw Bars
    const barWidth = (chartWidth / labels.length) * 0.6;
    const barSpacing = chartWidth / labels.length;
    
    labels.forEach((label, idx) => {
      const val = data[idx];
      const barHeight = (val / maxVal) * chartHeight;
      const x = padding.left + (barSpacing * idx) + (barSpacing - barWidth) / 2;
      const y = padding.top + chartHeight - barHeight;
      
      // Bar filling
      ctx.fillStyle = barColor;
      ctx.fillRect(x, y, barWidth, barHeight);
      
      // Draw label below bar
      ctx.fillStyle = textColor;
      ctx.textAlign = 'center';
      ctx.fillText(label, x + barWidth / 2, padding.top + chartHeight + 18);
    });
  }

  function drawLineChart(canvasId, labels, datasets) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    
    const ctx = canvas.getContext('2d');
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    
    const width = rect.width;
    const height = rect.height;
    
    ctx.clearRect(0, 0, width, height);
    
    const padding = { top: 20, right: 20, bottom: 40, left: 45 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    
    const gridColor = '#21262d';
    const textColor = '#8b949e';
    
    // Find absolute maximum among all datasets
    let maxVal = 0;
    datasets.forEach(ds => {
      maxVal = Math.max(maxVal, ...ds.data);
    });
    maxVal = maxVal * 1.15 || 10;
    
    // Y Gridlines
    const gridLines = 4;
    ctx.font = '10px Inter, sans-serif';
    ctx.fillStyle = textColor;
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 0.5;
    ctx.textAlign = 'right';

    for (let i = 0; i <= gridLines; i++) {
      const val = (maxVal / gridLines) * i;
      const y = padding.top + chartHeight - (chartHeight / gridLines) * i;
      
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      
      ctx.fillText(Math.round(val), padding.left - 12, y + 3);
    }

    // Draw X labels
    const pointsCount = labels.length;
    const pointSpacing = chartWidth / (pointsCount - 1);
    
    ctx.textAlign = 'center';
    labels.forEach((label, idx) => {
      const x = padding.left + pointSpacing * idx;
      ctx.fillText(label, x, padding.top + chartHeight + 18);
    });

    // Draw Lines
    datasets.forEach(ds => {
      ctx.strokeStyle = ds.color;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      
      ds.data.forEach((val, idx) => {
        const x = padding.left + pointSpacing * idx;
        const y = padding.top + chartHeight - (val / maxVal) * chartHeight;
        
        if (idx === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();
      
      // Draw Points
      ctx.fillStyle = ds.color;
      ds.data.forEach((val, idx) => {
        const x = padding.left + pointSpacing * idx;
        const y = padding.top + chartHeight - (val / maxVal) * chartHeight;
        
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#0d1117';
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = ds.color;
      });
    });
  }

  function renderAnalyticsCharts() {
    // 1. Congestion Load Peak Hours
    drawBarChart(
      'congestionTrendChart',
      'Congestion Load %',
      ['8 AM', '11 AM', '2 PM', '5 PM', '8 PM', '10 PM'],
      [68, 45, 52, 92, 85, 40],
      '#f85149' // Red
    );

    // 2. Average Resolution Times
    drawBarChart(
      'resolutionTimeChart',
      'Resolution Time (Mins)',
      ['Accident', 'Breakdown', 'Waterlog', 'Signals', 'Special'],
      [14, 22, 45, 12, 30],
      '#58a6ff' // Blue
    );

    // 3. Weekly Peak Congestion
    drawLineChart(
      'weeklyTrendChart',
      ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      [
        { color: '#e3b341', data: [75, 80, 85, 82, 94, 60, 45] } // Amber line
      ]
    );

    // 4. Mitigation Effectiveness
    drawBarChart(
      'mitigationImpactChart',
      'Impact %',
      ['Silk Board', 'Hebbal', 'Majestic', 'Indiranagar', 'ORR'],
      [28, 15, 34, 40, 22],
      '#3fb950' // Green
    );
  }

  // ==========================================
  // 10. SIMULATED LIVE UPDATES (DYNAMICS)
  // ==========================================

  function runLiveSimulation() {
    setInterval(() => {
      // 1. Fluctuating speeds slightly
      Object.keys(junctions).forEach(key => {
        const j = junctions[key];
        const variance = Math.floor(Math.random() * 7) - 3; // -3 to +3
        j.currentSpeed = Math.max(5, Math.min(j.baseSpeed + 10, j.currentSpeed + variance));
      });

      // 2. Occasionally add or clear moderate incidents
      if (Math.random() > 0.8) {
        // Toggle an incident state
        const luckyJunctionKeys = Object.keys(junctions);
        const randJunctionKey = luckyJunctionKeys[Math.floor(Math.random() * luckyJunctionKeys.length)];
        const matchingInc = incidents.find(i => i.junctionId === randJunctionKey);
        
        if (matchingInc) {
          matchingInc.active = !matchingInc.active;
        } else {
          // Add moderate temporary delay incident
          const newIncId = `inc_${Date.now()}`;
          incidents.push({
            id: newIncId,
            junctionId: randJunctionKey,
            title: 'Congestion Build-up',
            severity: 'moderate',
            desc: 'Traffic queuing due to volume peak bottlenecking.',
            time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }),
            active: true
          });
        }
      }

      // Cleanup resolved/inactive incidents from array to prevent bloat
      if (incidents.length > 8) {
        incidents = incidents.filter(i => i.active);
      }

      // 3. Dynamically update overall metrics based on junction averages
      let totalSpeed = 0;
      let totalMaxSpeed = 0;
      Object.values(junctions).forEach(j => {
        totalSpeed += j.currentSpeed;
        totalMaxSpeed += j.baseSpeed;
      });
      const avgSpeed = (totalSpeed / Object.keys(junctions).length).toFixed(1);
      document.getElementById('avgSpeedValue').textContent = `${avgSpeed} km/h`;

      const criticalIncCount = incidents.filter(i => i.severity === 'critical' && i.active).length;
      const indexValue = (criticalIncCount * 1.5 + (1 - totalSpeed / totalMaxSpeed) * 5).toFixed(1);
      document.getElementById('gridlockIndexValue').textContent = `${Math.min(10, Math.max(1, indexValue))} / 10`;

      // 4. Repaint the views
      renderMap();
      renderIncidentsList();
      if (selectedJunctionId) {
        updateJunctionInspector(selectedJunctionId);
      }
    }, 4000);
  }

  // ==========================================
  // 11. BOOTSTRAP APPLICATION
  // ==========================================

  initClock();
  initTabs();
  initFilters();
  renderMap();
  renderIncidentsList();
  renderForecasts();
  renderDeployment();
  initDispatchForm();
  
  // Set default inspector to Silk Board
  selectJunction('silkboard');
  
  // Pre-render analytics data once layout settles
  setTimeout(renderAnalyticsCharts, 200);

  // Start simulation loops
  runLiveSimulation();
});
