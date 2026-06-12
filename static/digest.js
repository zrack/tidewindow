const params = new URLSearchParams(window.location.search);
const elements = {
  context: document.querySelector("#digest-context"),
  meta: document.querySelector("#digest-meta"),
  summary: document.querySelector("#digest-summary"),
  content: document.querySelector("#digest-content"),
  copy: document.querySelector("#digest-copy"),
  share: document.querySelector("#digest-native-share"),
  calendar: document.querySelector("#digest-calendar"),
  status: document.querySelector("#digest-copy-status"),
};

let digestPayload = null;

initializeDigest();

async function initializeDigest() {
  const query = normalizedQuery();
  elements.calendar.href = `/api/digest.ics?${query.toString()}`;
  try {
    const response = await fetch(`/api/digest?${query.toString()}`);
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    digestPayload = await response.json();
    renderDigest(digestPayload);
    wireActions();
  } catch (error) {
    elements.meta.textContent = "Unavailable";
    elements.summary.textContent = "Unable to load this digest.";
    elements.content.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function normalizedQuery() {
  const query = new URLSearchParams();
  query.set("region", params.get("region") || "gig_harbor");
  query.set("risk", params.get("risk") || "standard");
  query.set("activity", normalizeActivity(params.get("activity")));
  const limit = params.get("limit");
  if (limit) query.set("limit", limit);
  return query;
}

function normalizeActivity(activity) {
  const value = String(activity || "All").toLowerCase();
  if (value === "kayak") return "Kayak";
  if (value === "fish" || value === "fishing") return "Fish";
  return "All";
}

function renderDigest(payload) {
  const region = payload.config?.region || {};
  const risk = payload.config?.risk_tolerance || {};
  const tomorrow = payload.digest?.tomorrow || {};
  const items = tomorrow.items || [];
  elements.context.textContent = `${region.name || "Puget Sound"} Marine Windows`;
  elements.meta.textContent = `${payload.activity || "All"} | ${risk.label || titleCase(risk.id || "standard")} risk`;
  elements.summary.textContent = tomorrow.summary || "No tomorrow recommendations are available yet.";

  if (!items.length) {
    elements.content.innerHTML = `<div class="empty">${escapeHtml(elements.summary.textContent)}</div>`;
    return;
  }

  elements.content.innerHTML = items.map((item) => `
    <article class="digest-card status-border-${escapeHtml(item.color || "yellow")}">
      <header>
        <div>
          <p class="digest-kicker">${escapeHtml(item.activity)} | ${escapeHtml(formatDigestDate(item.start))}</p>
          <h3>${escapeHtml(item.zone_title)}</h3>
        </div>
        ${statusPill(item.status)}
      </header>
      <p class="digest-time">${escapeHtml(formatTime(item.start))}-${escapeHtml(formatTime(item.end))}</p>
      <div class="digest-metrics">
        ${metric("Current", `${Number(item.current).toFixed(1)} kt`)}
        ${metric("Wind", `${Number(item.wind).toFixed(0)} kt`)}
        ${metric("Tide", `${Number(item.tide).toFixed(1)} ft`)}
      </div>
      <p class="digest-why">${escapeHtml(item.why)}</p>
      <p class="notice">${escapeHtml(item.note)}</p>
    </article>
  `).join("");
}

function wireActions() {
  elements.copy.addEventListener("click", async () => {
    await copyText(digestText());
    elements.status.textContent = "Copied";
  });
  elements.share.addEventListener("click", async () => {
    const text = digestText();
    const url = window.location.href;
    if (navigator.share) {
      try {
        await navigator.share({ title: "TideWindow Tomorrow's Best", text, url });
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }
    await copyText(`${text}\n\n${url}`);
    elements.status.textContent = "Link copied";
  });
}

function digestText() {
  return digestPayload?.text || "TideWindow Tomorrow's Best";
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {}
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function statusPill(status) {
  const color = status === "DANGER" ? "red" : status === "SAFE" || status === "OPTIMAL" ? "green" : "yellow";
  return `<span class="status-pill status-${color}">${escapeHtml(status)}</span>`;
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatDigestDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Tomorrow";
  return date.toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" });
}

function titleCase(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
