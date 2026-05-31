const state = {
  data: null,
  filter: "All",
  autoRefreshMs: 5 * 60 * 1000,
  nextRefreshAt: null,
  refreshTimer: null,
};

const zoneDetails = {
  purdy_bridge: {
    local: "Bridge and spit constriction can accelerate flow quickly.",
    kayak: "Safe at 1.0 kt or less, caution above 1.0 kt, danger above 2.0 kt.",
    fish: "Optimal from 1.0-3.0 kt, poor near slack, danger above 3.0 kt.",
  },
  gig_harbor: {
    local: "Protected harbor water with wind as the main comfort limiter.",
    kayak: "Safe through 15 kt wind, caution above 15 kt.",
    fish: "Optimal above 8.0 ft tide when bait pushes into the harbor edges.",
  },
  fox_island: {
    local: "Hale Passage has exposure to fetch and current around the bridge.",
    kayak: "Safe at 8 kt wind or less and 1.0 kt current or less, caution above either, danger above 12 kt wind or 2.0 kt current.",
    fish: "Optimal from 0.5-2.0 kt current; wait for more movement outside that band.",
  },
  sunrise_beach: {
    local: "Open shoreline with landing conditions that degrade in chop.",
    kayak: "Safe at 9 kt wind or less and 1.0 kt current or less, caution above either, danger above 14 kt wind or 1.8 kt current.",
    fish: "Optimal from 0.4-1.8 kt current along the beach structure.",
  },
  narrows_park: {
    local: "Narrows shoreline conditions can change fast as current builds.",
    kayak: "Safe at 8 kt wind or less and 0.8 kt current or less, caution above either, danger above 12 kt wind or 1.8 kt current.",
    fish: "Optimal from 0.5-1.8 kt current, caution below that, danger above 2.5 kt.",
  },
  fox_island_pier: {
    local: "Pier structure adds fishable edges but also exposure to wind chop.",
    kayak: "Safe at 8 kt wind or less and 1.0 kt current or less, caution above either, danger above 12 kt wind or 2.0 kt current.",
    fish: "Optimal from 0.5-2.0 kt current around structure and drop-offs.",
  },
  purdy_sand_spit: {
    local: "Spit edges concentrate flow near Purdy Bridge.",
    kayak: "Safe at 1.0 kt current or less, caution above 1.0 kt or 12 kt wind, danger above 2.0 kt current.",
    fish: "Optimal from 1.0-2.8 kt current, poor near slack, danger above 3.0 kt.",
  },
  kopachuck: {
    local: "Henderson Bay beach exposure makes wind and landings matter.",
    kayak: "Safe at 9 kt wind or less and 1.0 kt current or less, caution above either, danger above 15 kt wind or 1.8 kt current.",
    fish: "Optimal above 8.0 ft tide with more than 0.3 kt current.",
  },
};

const elements = {
  refresh: document.querySelector("#refresh-button"),
  confidenceLevel: document.querySelector("#confidence-level"),
  confidenceNote: document.querySelector("#confidence-note"),
  sourceLine: document.querySelector("#source-line"),
  sourceNote: document.querySelector("#source-note"),
  updatedAt: document.querySelector("#updated-at"),
  zonesGrid: document.querySelector("#zones-grid"),
  windowsGrid: document.querySelector("#windows-grid"),
  windowCount: document.querySelector("#window-count"),
  tideChart: document.querySelector("#tide-chart"),
  filterButtons: document.querySelectorAll(".filter-button"),
  zoneDialog: document.querySelector("#zone-dialog"),
  zoneDialogClose: document.querySelector("#zone-dialog-close"),
  zoneDialogContent: document.querySelector("#zone-dialog-content"),
};

elements.refresh.addEventListener("click", loadState);
elements.zoneDialogClose.addEventListener("click", () => elements.zoneDialog.close());
elements.zoneDialog.addEventListener("click", (event) => {
  if (event.target === elements.zoneDialog) elements.zoneDialog.close();
});
elements.filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    elements.filterButtons.forEach((item) => item.classList.toggle("active", item === button));
    renderWindows();
  });
});

loadState();
scheduleAutoRefresh();

async function loadState() {
  elements.refresh.disabled = true;
  elements.zonesGrid.innerHTML = `<div class="loading">Loading marine areas...</div>`;
  elements.windowsGrid.innerHTML = `<div class="loading">Loading forecast windows...</div>`;

  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    state.data = await response.json();
    state.autoRefreshMs = Math.max(30, Number(state.data.config?.refresh_seconds || 300)) * 1000;
    renderSummary();
    renderWindows();
    renderZones();
    drawTideChart();
    scheduleAutoRefresh();
  } catch (error) {
    elements.windowsGrid.innerHTML = `<div class="empty">Unable to load TideWindow data. ${escapeHtml(error.message)}</div>`;
    elements.zonesGrid.innerHTML = "";
  } finally {
    elements.refresh.disabled = false;
  }
}

function scheduleAutoRefresh() {
  if (state.refreshTimer) clearTimeout(state.refreshTimer);
  state.nextRefreshAt = new Date(Date.now() + state.autoRefreshMs);
  updateRefreshLine();
  state.refreshTimer = setTimeout(loadState, state.autoRefreshMs);
}

function renderSummary() {
  const { confidence, telemetry, forecast, generated_at } = state.data;
  elements.confidenceLevel.textContent = confidence.level;
  elements.confidenceLevel.className = `status-${confidence.color}`;
  elements.confidenceNote.textContent = confidence.note;

  const telemetrySources = telemetry.sources || {};
  const forecastSources = forecast.sources || {};
  elements.sourceLine.textContent = sourceHeadline(telemetrySources, forecastSources);
  elements.sourceNote.innerHTML = dataStatusRows(telemetry, forecast);
  updateRefreshLine(generated_at);
}

function updateRefreshLine(generatedAt = state.data?.generated_at) {
  if (!generatedAt) {
    elements.updatedAt.textContent = "Updated when data loads";
    return;
  }

  const nextRefresh = state.nextRefreshAt ? ` | Next ${formatTime(state.nextRefreshAt)}` : "";
  elements.updatedAt.textContent = `Updated ${formatDateTime(generatedAt)}${nextRefresh}`;
}

function renderWindows() {
  if (!state.data) return;

  const windows = state.data.windows.filter((window) => {
    return state.filter === "All" || window.activity === state.filter;
  });
  elements.windowCount.textContent = `${windows.length} shown`;

  if (!windows.length) {
    elements.windowsGrid.innerHTML = `<div class="empty">No ${state.filter.toLowerCase()} windows available.</div>`;
    return;
  }

  elements.windowsGrid.innerHTML = windows.map((window) => `
    <article class="window-card">
      <header>
        <div>
          <h3>${escapeHtml(window.zone_title)}</h3>
          <p class="window-meta">${escapeHtml(window.activity)} | ${escapeHtml(window.phase)}</p>
        </div>
        ${statusPill(window.status)}
      </header>
      <p class="window-time">${formatTime(window.start)}-${formatTime(window.end)}</p>
      <p class="window-meta">${window.current.toFixed(1)} kt current | ${window.wind.toFixed(0)} kt wind (${escapeHtml(window.wind_source)})</p>
      <p class="notice">${escapeHtml(window.note)}</p>
    </article>
  `).join("");
}

function renderZones() {
  elements.zonesGrid.innerHTML = state.data.zones.map((zone) => `
    <article class="zone-card">
      <header>
        <h3>${escapeHtml(zone.title)}</h3>
        ${statusPill(zone.kayak.status)}
      </header>
      <div class="metrics">
        ${metric("Current", `${zone.current.toFixed(2)} kt`)}
        ${metric("Wind", `${zone.wind.toFixed(1)} kt`)}
        ${metric("Tide", `${zone.tide.toFixed(1)} ft`)}
      </div>
      <div class="activity-grid">
        ${activity("Kayak", zone.kayak)}
        ${activity("Fish", zone.fish)}
      </div>
      <button class="details-button" type="button" data-zone-id="${escapeHtml(zone.id)}">Details</button>
    </article>
  `).join("");

  elements.zonesGrid.querySelectorAll(".details-button").forEach((button) => {
    button.addEventListener("click", () => openZoneDetails(button.dataset.zoneId));
  });
}

function openZoneDetails(zoneId) {
  const zone = state.data.zones.find((item) => item.id === zoneId);
  if (!zone) return;

  const details = zoneDetails[zoneId] || {
    local: "Local zone thresholds are based on current TideWindow scoring rules.",
    kayak: "Kayak scoring uses local current and wind thresholds.",
    fish: "Fishing scoring uses local current and tide thresholds.",
  };

  elements.zoneDialogContent.innerHTML = `
    <p class="eyebrow">Zone detail</p>
    <h2 id="zone-dialog-title">${escapeHtml(zone.title)}</h2>
    <div class="detail-metrics">
      ${metric("Current", `${zone.current.toFixed(2)} kt`)}
      ${metric("Wind", `${zone.wind.toFixed(1)} kt`)}
      ${metric("Tide", `${zone.tide.toFixed(1)} ft`)}
    </div>
    <p class="detail-note">${escapeHtml(details.local)}</p>
    ${detailRule("Kayak", zone.kayak, details.kayak)}
    ${detailRule("Fish", zone.fish, details.fish)}
  `;
  elements.zoneDialog.showModal();
}

function detailRule(label, evaluation, rule) {
  return `
    <section class="detail-rule">
      <header>
        <h3>${escapeHtml(label)}</h3>
        ${statusPill(evaluation.status)}
      </header>
      <p>${escapeHtml(evaluation.note)}</p>
      <p class="notice">${escapeHtml(rule)}</p>
    </section>
  `;
}

function drawTideChart() {
  const canvas = elements.tideChart;
  const ctx = canvas.getContext("2d");
  const points = state.data.forecast.predictions || [];
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (points.length < 2) {
    ctx.fillStyle = "#9caeaf";
    ctx.fillText("No tide forecast", 16, 64);
    return;
  }

  const values = points.map((point) => point.tide_feet);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = 14;
  const width = canvas.width - pad * 2;
  const height = canvas.height - pad * 2;

  ctx.strokeStyle = "#2b3a40";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad, canvas.height - pad);
  ctx.lineTo(canvas.width - pad, canvas.height - pad);
  ctx.stroke();

  ctx.strokeStyle = "#00c2c7";
  ctx.lineWidth = 3;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = pad + (index / (values.length - 1)) * width;
    const y = pad + (1 - ((value - min) / Math.max(max - min, 0.01))) * height;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#9caeaf";
  ctx.font = "12px system-ui";
  ctx.fillText(`${min.toFixed(1)} ft`, pad, canvas.height - 4);
  ctx.fillText(`${max.toFixed(1)} ft`, pad, 12);
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function activity(label, evaluation) {
  return `
    <div class="activity status-${evaluation.color}">
      <strong>${label}: ${escapeHtml(evaluation.status)}</strong>
      <p class="notice">${escapeHtml(evaluation.note)}</p>
    </div>
  `;
}

function statusPill(status) {
  const color = status === "DANGER" ? "red" : status === "SAFE" || status === "OPTIMAL" ? "green" : "yellow";
  return `<span class="status-pill status-${color}">${escapeHtml(status)}</span>`;
}

function dataStatusRows(telemetry, forecast) {
  const telemetrySources = telemetry.sources || {};
  const forecastSources = forecast.sources || {};
  const rows = [
    statusRow("Now", telemetrySources, telemetry.fallback_reason),
    statusRow("Forecast", forecastSources, forecast.fallback_reason || forecast.wind_fallback_reason),
  ];

  const notices = [
    telemetry.fallback_reason && `Now: ${telemetry.fallback_reason}`,
    forecast.fallback_reason && `Forecast: ${forecast.fallback_reason}`,
    forecast.wind_fallback_reason && `Wind: ${forecast.wind_fallback_reason}`,
  ].filter(Boolean);

  if (notices.length) {
    rows.push(`<p class="source-reason">${escapeHtml(notices.join(" | "))}</p>`);
  }

  return rows.join("");
}

function statusRow(label, sources, reason) {
  const health = reason ? "yellow" : Object.values(sources).includes("seed") || Object.values(sources).includes("fallback") ? "yellow" : "green";
  return `
    <div class="source-row">
      <span>${escapeHtml(label)}</span>
      <strong class="status-${health}">${sourceText(sources)}</strong>
    </div>
  `;
}

function sourceHeadline(telemetrySources, forecastSources) {
  const sourceValues = [
    ...Object.values(telemetrySources),
    ...Object.values(forecastSources),
  ];
  if (sourceValues.includes("seed")) return "Seed data active";
  if (sourceValues.includes("fallback") || sourceValues.includes("missing")) return "Partial live data";
  return "Live data";
}

function sourceText(sources) {
  return `Tide ${sources.tide || "unknown"}, Current ${sources.current || "unknown"}, Wind ${sources.wind || "unknown"}`;
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatDateTime(value) {
  return new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
