const storageKeys = {
  filter: "tidewindow.filter",
  visibleZones: "tidewindow.visibleZones",
};

const state = {
  data: null,
  filter: localStorage.getItem(storageKeys.filter) || "All",
  autoRefreshMs: 5 * 60 * 1000,
  nextRefreshAt: null,
  refreshTimer: null,
  visibleZoneIds: [],
  leafletMap: null,
  leafletMarkers: [],
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
  wollochet_bay: {
    local: "Protected bay water with current muted by the basin shape.",
    kayak: "Generic kayak scoring applies; wind is usually the main limiter.",
    fish: "Generic fishing scoring applies; moving water is better than slack.",
  },
  horsehead_bay: {
    local: "Sheltered Henderson Bay pocket that can still feel exposed in wind.",
    kayak: "Generic kayak scoring applies with reduced current exposure.",
    fish: "Generic fishing scoring applies; watch for movement along the shoreline.",
  },
  raft_island: {
    local: "Island shoreline with mixed exposure around Hale Passage.",
    kayak: "Generic kayak scoring applies; watch wind direction and chop.",
    fish: "Generic fishing scoring applies around shoreline structure.",
  },
  rosedale_beach: {
    local: "Inner-harbor shoreline option with generally softer current.",
    kayak: "Generic kayak scoring applies with lighter current assumptions.",
    fish: "Generic fishing scoring applies; higher water can help beach edges.",
  },
  point_fosdick: {
    local: "Transition shoreline between harbor protection and Narrows exposure.",
    kayak: "Generic kayak scoring applies; wind and current can both matter.",
    fish: "Generic fishing scoring applies; moving water improves the read.",
  },
};

const elements = {
  refresh: document.querySelector("#refresh-button"),
  confidenceLevel: document.querySelector("#confidence-level"),
  confidenceNote: document.querySelector("#confidence-note"),
  sourceLine: document.querySelector("#source-line"),
  sourceNote: document.querySelector("#source-note"),
  updatedAt: document.querySelector("#updated-at"),
  windowsGrid: document.querySelector("#windows-grid"),
  windowCount: document.querySelector("#window-count"),
  tideChart: document.querySelector("#tide-chart"),
  filterButtons: document.querySelectorAll(".filter-button"),
  zoneDialog: document.querySelector("#zone-dialog"),
  zoneDialogClose: document.querySelector("#zone-dialog-close"),
  zoneDialogContent: document.querySelector("#zone-dialog-content"),
  zoneMap: document.querySelector("#zone-map"),
  mapMode: document.querySelector("#map-mode"),
  timelineStrip: document.querySelector("#timeline-strip"),
  timelineCount: document.querySelector("#timeline-count"),
  tideEvents: document.querySelector("#tide-events"),
  slackEvents: document.querySelector("#slack-events"),
  eventsNote: document.querySelector("#events-note"),
  locationCount: document.querySelector("#location-count"),
  locationSelect: document.querySelector("#location-select"),
  locationAdd: document.querySelector("#location-add"),
  locationReset: document.querySelector("#location-reset"),
};

elements.refresh.addEventListener("click", loadState);
elements.zoneDialogClose.addEventListener("click", () => elements.zoneDialog.close());
elements.zoneDialog.addEventListener("click", (event) => {
  if (event.target === elements.zoneDialog) elements.zoneDialog.close();
});
elements.locationAdd.addEventListener("click", addSelectedLocation);
elements.locationReset.addEventListener("click", restoreDefaultLocations);
elements.filterButtons.forEach((button) => {
  button.addEventListener("click", () => setFilter(button.dataset.filter));
});

setFilter(state.filter, { render: false });
loadState();
scheduleAutoRefresh();

async function loadState() {
  elements.refresh.disabled = true;
  elements.windowsGrid.innerHTML = `<div class="loading">Loading forecast windows...</div>`;
  elements.timelineStrip.innerHTML = `<div class="loading">Loading hourly timeline...</div>`;
  if (elements.tideEvents) elements.tideEvents.innerHTML = `<div class="loading">Loading tide events...</div>`;
  if (elements.slackEvents) elements.slackEvents.innerHTML = `<div class="loading">Loading current events...</div>`;
  if (!state.leafletMap) {
    elements.zoneMap.innerHTML = `<div class="loading">Loading map...</div>`;
  }

  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    state.data = await response.json();
    state.autoRefreshMs = Math.max(30, Number(state.data.config?.refresh_seconds || 300)) * 1000;
    initializeVisibleLocations();
    renderDashboard();
    scheduleAutoRefresh();
  } catch (error) {
    elements.windowsGrid.innerHTML = `<div class="empty">Unable to load TideWindow data. ${escapeHtml(error.message)}</div>`;
    elements.timelineStrip.innerHTML = "";
    if (!state.leafletMap) {
      elements.zoneMap.innerHTML = "";
    }
  } finally {
    elements.refresh.disabled = false;
  }
}

function renderDashboard() {
  renderSummary();
  renderLocationControls();
  renderMap();
  renderEvents();
  renderTimeline();
  renderWindows();
  drawTideChart();
}

function scheduleAutoRefresh() {
  if (state.refreshTimer) clearTimeout(state.refreshTimer);
  state.nextRefreshAt = new Date(Date.now() + state.autoRefreshMs);
  updateRefreshLine();
  state.refreshTimer = setTimeout(loadState, state.autoRefreshMs);
}

function setFilter(filter, options = {}) {
  state.filter = ["All", "Kayak", "Fish"].includes(filter) ? filter : "All";
  localStorage.setItem(storageKeys.filter, state.filter);
  elements.filterButtons.forEach((item) => {
    item.classList.toggle("active", item.dataset.filter === state.filter);
  });

  if (options.render !== false && state.data) {
    renderMap();
    renderTimeline();
    renderWindows();
  }
}

function initializeVisibleLocations() {
  const allIds = state.data.zones.map((zone) => zone.id);
  const defaults = state.data.zones.filter((zone) => zone.active_by_default).map((zone) => zone.id);
  let stored = [];

  try {
    stored = JSON.parse(localStorage.getItem(storageKeys.visibleZones) || "[]");
  } catch {
    stored = [];
  }

  const validStored = stored.filter((id) => allIds.includes(id));
  state.visibleZoneIds = validStored.length ? validStored : defaults;
  saveVisibleLocations();
}

function saveVisibleLocations() {
  localStorage.setItem(storageKeys.visibleZones, JSON.stringify(state.visibleZoneIds));
}

function visibleZones() {
  const visible = new Set(state.visibleZoneIds);
  return state.data.zones.filter((zone) => visible.has(zone.id));
}

function availableZones() {
  const visible = new Set(state.visibleZoneIds);
  return state.data.zones.filter((zone) => !visible.has(zone.id));
}

function addSelectedLocation() {
  const zoneId = elements.locationSelect.value;
  if (!zoneId || state.visibleZoneIds.includes(zoneId)) return;
  state.visibleZoneIds.push(zoneId);
  saveVisibleLocations();
  renderLocationDrivenViews();
}

function hideLocation(zoneId) {
  if (state.visibleZoneIds.length <= 1) return;
  state.visibleZoneIds = state.visibleZoneIds.filter((id) => id !== zoneId);
  saveVisibleLocations();
  renderLocationDrivenViews();
}

function restoreDefaultLocations() {
  state.visibleZoneIds = state.data.zones.filter((zone) => zone.active_by_default).map((zone) => zone.id);
  saveVisibleLocations();
  renderLocationDrivenViews();
}

function renderLocationDrivenViews() {
  renderLocationControls();
  renderMap();
  renderTimeline();
  renderWindows();
}

function renderSummary() {
  const { confidence, telemetry, forecast, generated_at } = state.data;
  elements.confidenceLevel.textContent = confidence.level;
  elements.confidenceLevel.className = `status-${confidence.color}`;
  elements.confidenceNote.textContent = confidence.note;

  const telemetrySources = telemetry.sources || {};
  const forecastSources = forecast.sources || {};
  const cache = state.data.cache || {};
  const stale = Boolean(cache.telemetry_stale || cache.forecast_stale);
  elements.sourceLine.textContent = stale
    ? "Showing last good data"
    : sourceHeadline(telemetrySources, forecastSources);
  elements.sourceLine.className = stale ? "status-yellow" : "";
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

function renderLocationControls() {
  const visible = visibleZones();
  const available = availableZones();
  elements.locationCount.textContent = `${visible.length} visible | ${available.length} addable`;
  elements.locationSelect.innerHTML = available.length
    ? available.map((zone) => `<option value="${escapeHtml(zone.id)}">${escapeHtml(zone.title)}</option>`).join("")
    : `<option value="">All locations are visible</option>`;
  elements.locationAdd.disabled = !available.length;
}

function renderMap() {
  const zones = visibleZones();
  const mode = state.filter === "Fish" ? "Fish" : "Kayak";
  elements.mapMode.textContent = `${mode} status | ${zones.length} visible`;

  if (!zones.length) {
    elements.zoneMap.innerHTML = `<div class="empty">No visible locations.</div>`;
    return;
  }

  if (!window.L) {
    elements.zoneMap.innerHTML = `<div class="empty">Leaflet map assets did not load.</div>`;
    return;
  }

  initializeLeafletMap();
  state.leafletMarkers.forEach((marker) => marker.remove());
  state.leafletMarkers = [];

  const bounds = [];
  zones.forEach((zone) => {
    if (!zone.map?.lat || !zone.map?.lon) return;
    const evaluation = mode === "Fish" ? zone.fish : zone.kayak;
    const marker = L.circleMarker([zone.map.lat, zone.map.lon], {
      className: `leaflet-status-circle status-${evaluation.color}`,
      radius: 9,
      color: statusColor(evaluation.color),
      fillColor: statusColor(evaluation.color),
      fillOpacity: 0.72,
      weight: 3,
      title: zone.title,
    });

    marker.bindTooltip(`${zone.title}: ${evaluation.status}`, {
      direction: "top",
      offset: [0, -12],
    });
    marker.bindPopup(zonePopup(zone, zones.length), {
      className: "zone-map-popup",
      closeButton: true,
      maxWidth: 360,
      minWidth: 300,
    });
    marker.on("popupopen", (event) => wireZonePopup(event.popup.getElement(), zone.id));
    marker.addTo(state.leafletMap);
    state.leafletMarkers.push(marker);
    bounds.push([zone.map.lat, zone.map.lon]);
  });

  if (bounds.length > 1) {
    state.leafletMap.fitBounds(bounds, { padding: [38, 38], maxZoom: 12 });
  } else if (bounds.length === 1) {
    state.leafletMap.setView(bounds[0], 12);
  }
  setTimeout(() => state.leafletMap.invalidateSize(), 0);
}

function initializeLeafletMap() {
  if (state.leafletMap) return;

  elements.zoneMap.innerHTML = "";
  state.leafletMap = L.map(elements.zoneMap, {
    center: [47.32, -122.61],
    zoom: 11,
    scrollWheelZoom: false,
  });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(state.leafletMap);
}

function renderEvents() {
  if (!elements.tideEvents || !elements.slackEvents) return;

  const forecast = state.data.forecast || {};
  const tideEvents = (forecast.tide_events || []).slice(0, 6);
  const slackEvents = (forecast.slack_events || []).slice(0, 6);

  elements.tideEvents.innerHTML = tideEvents.length
    ? tideEvents.map((event) => eventRow({
        time: event.time,
        label: event.type,
        value: `${Number(event.tide_feet).toFixed(1)} ft`,
        icon: event.type === "Low" ? "▼" : "▲",
        tone: event.type === "Low" ? "low" : "high",
      })).join("")
    : `<div class="empty">No tide events available.</div>`;

  elements.slackEvents.innerHTML = slackEvents.length
    ? slackEvents.map((event) => eventRow({
        time: event.time,
        label: event.type,
        value: event.type === "Slack" ? "slack" : `${Number(event.speed).toFixed(1)} kt`,
        icon: event.type === "Slack" ? "○" : "→",
        tone: event.type === "Slack" ? "slack" : "current",
      })).join("")
    : `<div class="empty">No current events available.</div>`;
}

function eventRow({ time, label, value, icon, tone }) {
  return `
    <div class="event-row">
      <span class="event-time">${escapeHtml(formatTime(time))}</span>
      <span class="event-type event-${escapeHtml(tone)}"><span class="event-icon" aria-hidden="true">${icon}</span>${escapeHtml(label)}</span>
      <span class="event-value">${escapeHtml(value)}</span>
      <span class="event-when">${escapeHtml(relativeTime(time))}</span>
    </div>
  `;
}

function relativeTime(value) {
  const deltaMs = new Date(value).getTime() - Date.now();
  if (Number.isNaN(deltaMs)) return "";
  if (deltaMs <= 0) return "now";
  const minutes = Math.round(deltaMs / 60000);
  if (minutes < 60) return `in ${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `in ${hours}h ${remainder}m` : `in ${hours}h`;
}

function renderTimeline() {
  const visible = new Set(state.visibleZoneIds);
  const items = (state.data.timeline || []).slice(0, 24);
  elements.timelineCount.textContent = `${items.length} hours${daylightCaption()}`;

  if (!items.length) {
    elements.timelineStrip.innerHTML = `<div class="empty">No hourly tide timeline available.</div>`;
    return;
  }

  elements.timelineStrip.innerHTML = items.map((item) => {
    const kayak = bestTimelineZone(item, "Kayak", visible);
    const fish = bestTimelineZone(item, "Fish", visible);
    const main = state.filter === "Fish" ? fish : kayak;
    const color = main?.evaluation.color || "yellow";
    const light = daylightPhase(item.start);

    return `
      <article class="timeline-hour status-border-${color} light-${light}">
        <p class="timeline-time"><span class="hour-glyph" aria-hidden="true">${light === "night" ? "☾" : "☀"}</span>${formatTime(item.start)}</p>
        <p class="timeline-metric">${item.tide.toFixed(1)} ft | ${item.wind.toFixed(0)} kt</p>
        <p class="timeline-phase">${escapeHtml(item.phase)}</p>
        ${state.filter === "All" ? timelinePair(kayak, fish) : timelineSingle(main, state.filter)}
      </article>
    `;
  }).join("");
}

function daylightFor(isoTime) {
  const daylight = state.data.daylight || {};
  const key = String(isoTime).slice(0, 10);
  return daylight[key] || null;
}

function daylightPhase(isoTime) {
  const day = daylightFor(isoTime);
  if (!day || !day.sunrise || !day.sunset) return "day";
  const t = new Date(isoTime).getTime();
  const sunrise = new Date(day.sunrise).getTime();
  const sunset = new Date(day.sunset).getTime();
  if (t < sunrise || t >= sunset) return "night";
  const goldenMs = 60 * 60 * 1000;
  if (t < sunrise + goldenMs || t >= sunset - goldenMs) return "golden";
  return "day";
}

function daylightCaption() {
  const day = daylightFor(state.data.timeline?.[0]?.start || state.data.generated_at);
  if (!day || !day.sunrise || !day.sunset) return "";
  return ` · ☀ ${formatTime(day.sunrise)}–${formatTime(day.sunset)}`;
}

function bestTimelineZone(item, activity, visible) {
  const key = activity === "Fish" ? "fish" : "kayak";
  const scoreKey = `${key}_score`;
  let best = null;

  Object.entries(item.zones || {}).forEach(([zoneId, zone]) => {
    if (!visible.has(zoneId)) return;
    if (!best || zone[scoreKey] > best.score) {
      best = {
        zoneId,
        score: zone[scoreKey],
        evaluation: zone[key],
        title: zoneTitle(zoneId),
      };
    }
  });

  return best;
}

function timelinePair(kayak, fish) {
  return `
    <div class="timeline-pair">
      ${timelineBadge("Kayak", kayak)}
      ${timelineBadge("Fish", fish)}
    </div>
  `;
}

function timelineSingle(item, activity) {
  if (!item) return `<p class="notice">No visible ${activity.toLowerCase()} zone.</p>`;
  return `
    <div class="timeline-focus">
      <strong class="status-${item.evaluation.color}">${escapeHtml(item.evaluation.status)}</strong>
      <span>${escapeHtml(shortZoneTitle(item.title))}</span>
    </div>
  `;
}

function timelineBadge(label, item) {
  if (!item) return `<span>${escapeHtml(label)} none</span>`;
  return `<span class="status-${item.evaluation.color}">${escapeHtml(label)} ${escapeHtml(item.evaluation.status)}</span>`;
}

function renderWindows() {
  if (!state.data) return;

  const visible = new Set(state.visibleZoneIds);
  const windows = state.data.windows.filter((window) => {
    const activityMatch = state.filter === "All" || window.activity === state.filter;
    return activityMatch && visible.has(window.zone_id);
  });
  elements.windowCount.textContent = `${windows.length} shown`;

  if (!windows.length) {
    elements.windowsGrid.innerHTML = `<div class="empty">No ${state.filter.toLowerCase()} windows available for visible locations.</div>`;
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

function openZoneDetails(zoneId) {
  const zone = state.data.zones.find((item) => item.id === zoneId);
  if (!zone) return;

  const details = zoneDetailCopy(zoneId);

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

function zonePopup(zone, visibleCount) {
  const details = zoneDetailCopy(zone.id);
  return `
    <article class="map-spot-card">
      <header>
        <div>
          <p class="eyebrow">Map spot</p>
          <h3>${escapeHtml(zone.title)}</h3>
        </div>
        ${statusPill((state.filter === "Fish" ? zone.fish : zone.kayak).status)}
      </header>
      <div class="metrics">
        ${metric("Current", `${zone.current.toFixed(2)} kt`)}
        ${metric("Wind", `${zone.wind.toFixed(1)} kt`)}
        ${metric("Tide", `${zone.tide.toFixed(1)} ft`)}
      </div>
      <p class="detail-note">${escapeHtml(details.local)}</p>
      <div class="activity-grid">
        ${activity("Kayak", zone.kayak)}
        ${activity("Fish", zone.fish)}
      </div>
      <div class="map-rule-list">
        <p><strong>Kayak thresholds</strong> ${escapeHtml(details.kayak)}</p>
        <p><strong>Fish thresholds</strong> ${escapeHtml(details.fish)}</p>
      </div>
      <div class="card-actions">
        <button class="details-button" type="button" data-zone-id="${escapeHtml(zone.id)}">Details</button>
        <button class="hide-button" type="button" data-zone-id="${escapeHtml(zone.id)}" ${visibleCount <= 1 ? "disabled" : ""}>Hide</button>
      </div>
    </article>
  `;
}

function wireZonePopup(popupElement, zoneId) {
  if (!popupElement) return;
  const detailsButton = popupElement.querySelector(".details-button");
  const hideButton = popupElement.querySelector(".hide-button");

  detailsButton?.addEventListener("click", () => openZoneDetails(zoneId));
  hideButton?.addEventListener("click", () => hideLocation(zoneId));
}

function zoneDetailCopy(zoneId) {
  return zoneDetails[zoneId] || {
    local: "Local zone thresholds are based on current TideWindow scoring rules.",
    kayak: "Kayak scoring uses local current and wind thresholds.",
    fish: "Fishing scoring uses local current and tide thresholds.",
  };
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

function statusColor(color) {
  if (color === "red") return "#ff5b5b";
  if (color === "green") return "#49d17d";
  return "#e8c84a";
}

function dataStatusRows(telemetry, forecast) {
  const telemetrySources = telemetry.sources || {};
  const forecastSources = forecast.sources || {};
  const rows = [
    statusRow("Now", telemetrySources, telemetry.fallback_reason, telemetry.age_seconds, telemetry.stale),
    statusRow("Forecast", forecastSources, forecast.fallback_reason || forecast.wind_fallback_reason, forecast.age_seconds, forecast.stale),
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

function statusRow(label, sources, reason, ageSeconds, stale) {
  const degraded = ["seed", "fallback", "predicted", "missing"];
  const health = stale || reason ? "yellow" : Object.values(sources).some((value) => degraded.includes(value)) ? "yellow" : "green";
  const ageText = ageSeconds == null ? "" : formatAge(ageSeconds);
  const ageLabel = [ageText, stale ? "last good reading" : ""].filter(Boolean).join(" · ");
  return `
    <div class="source-row">
      <span>${escapeHtml(label)}</span>
      <div class="source-value">
        <strong class="status-${health}">${sourceText(sources)}</strong>
        ${ageLabel ? `<span class="source-age${stale ? " status-yellow" : ""}">${escapeHtml(ageLabel)}</span>` : ""}
      </div>
    </div>
  `;
}

function formatAge(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  if (total < 60) return "just now";
  const minutes = Math.round(total / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}h ${remainder}m ago` : `${hours}h ago`;
}

function sourceHeadline(telemetrySources, forecastSources) {
  const sourceValues = [
    ...Object.values(telemetrySources),
    ...Object.values(forecastSources),
  ];
  if (sourceValues.includes("seed")) return "Seed data active";
  if (["fallback", "missing", "predicted"].some((value) => sourceValues.includes(value))) return "Partial live data";
  return "Live data";
}

function sourceText(sources) {
  return `Tide ${sources.tide || "unknown"}, Current ${sources.current || "unknown"}, Wind ${sources.wind || "unknown"}`;
}

function zoneTitle(zoneId) {
  return state.data.zones.find((zone) => zone.id === zoneId)?.title || zoneId;
}

function shortZoneTitle(title) {
  return title
    .replace(" (HENDERSON BAY)", "")
    .replace(" (HALE PASSAGE)", "")
    .replace(" STATE PARK", "")
    .replace(" PARK", "")
    .replace(" SHORELINE", "");
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
