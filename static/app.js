const state = {
  data: null,
  filter: "All",
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
};

elements.refresh.addEventListener("click", loadState);
elements.filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.filter = button.dataset.filter;
    elements.filterButtons.forEach((item) => item.classList.toggle("active", item === button));
    renderWindows();
  });
});

loadState();

async function loadState() {
  elements.refresh.disabled = true;
  elements.zonesGrid.innerHTML = `<div class="loading">Loading marine areas...</div>`;
  elements.windowsGrid.innerHTML = `<div class="loading">Loading forecast windows...</div>`;

  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    state.data = await response.json();
    renderSummary();
    renderWindows();
    renderZones();
    drawTideChart();
  } catch (error) {
    elements.windowsGrid.innerHTML = `<div class="empty">Unable to load TideWindow data. ${escapeHtml(error.message)}</div>`;
    elements.zonesGrid.innerHTML = "";
  } finally {
    elements.refresh.disabled = false;
  }
}

function renderSummary() {
  const { confidence, telemetry, forecast, generated_at } = state.data;
  elements.confidenceLevel.textContent = confidence.level;
  elements.confidenceLevel.className = `status-${confidence.color}`;
  elements.confidenceNote.textContent = confidence.note;

  const telemetrySources = telemetry.sources || {};
  const forecastSources = forecast.sources || {};
  elements.sourceLine.textContent = `Now ${sourceText(telemetrySources)} | Forecast ${sourceText(forecastSources)}`;
  elements.sourceNote.textContent = compactNotice(telemetry, forecast);
  elements.updatedAt.textContent = `Updated ${formatDateTime(generated_at)}`;
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
    </article>
  `).join("");
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

function compactNotice(telemetry, forecast) {
  if (forecast.wind_fallback_reason) return "Hourly wind unavailable; using current wind for forecast scoring.";
  if (forecast.fallback_reason) return "Forecast fallback data is active.";
  if (telemetry.fallback_reason) return "Live NOAA telemetry unavailable; seed/current fallback data is active.";
  return "Live observations and forecast guidance are available.";
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
