const adminElements = {
  authPanel: document.querySelector("#admin-auth-panel"),
  authForm: document.querySelector("#admin-auth-form"),
  authToken: document.querySelector("#admin-token"),
  authStatus: document.querySelector("#admin-auth-status"),
  audit: document.querySelector("#admin-audit"),
  auditCount: document.querySelector("#admin-audit-count"),
  preferences: document.querySelector("#admin-preferences"),
  preferenceCount: document.querySelector("#admin-preference-count"),
  readiness: document.querySelector("#admin-readiness"),
  readinessStatus: document.querySelector("#admin-readiness-status"),
  actionStatus: document.querySelector("#admin-action-status"),
  health: document.querySelector("#admin-health"),
  healthStatus: document.querySelector("#admin-health-status"),
};
const adminTokenKey = "tidewindow.adminToken";

async function loadDigestAdmin() {
  try {
    const response = await adminFetch("/api/digest-admin?limit=50");
    const payload = await response.json();
    if (response.status === 401) {
      showAuthPanel(payload.detail || "Admin token is required.");
      return;
    }
    if (!response.ok) throw new Error(payload.detail || `API returned ${response.status}`);
    hideAuthPanel();
    renderHealth(payload.health || {});
    renderReadiness(payload.readiness || {});
    renderAudit(payload.audit || []);
    renderPreferences(payload.preferences || []);
  } catch (error) {
    const message = escapeHtml(error.message || "Unable to load digest admin.");
    adminElements.health.innerHTML = `<div class="empty">${message}</div>`;
    adminElements.readiness.innerHTML = `<div class="empty">${message}</div>`;
    adminElements.audit.innerHTML = `<div class="empty">${message}</div>`;
    adminElements.preferences.innerHTML = `<div class="empty">${message}</div>`;
  }
}

function wireAdminAuth() {
  const query = new URLSearchParams(window.location.search);
  const token = query.get("admin_token");
  if (token) {
    sessionStorage.setItem(adminTokenKey, token);
    query.delete("admin_token");
    const clean = `${window.location.pathname}${query.toString() ? `?${query.toString()}` : ""}`;
    window.history.replaceState({}, "", clean);
  }
  adminElements.authForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = adminElements.authToken.value.trim();
    if (!value) {
      adminElements.authStatus.textContent = "Token required";
      return;
    }
    sessionStorage.setItem(adminTokenKey, value);
    adminElements.authStatus.textContent = "Checking...";
    await loadDigestAdmin();
  });
}

function showAuthPanel(message) {
  adminElements.authPanel.hidden = false;
  adminElements.authStatus.textContent = message;
}

function hideAuthPanel() {
  adminElements.authPanel.hidden = true;
  adminElements.authStatus.textContent = "";
}

function adminFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = sessionStorage.getItem(adminTokenKey);
  if (token) headers.set("X-TideWindow-Admin-Token", token);
  return fetch(path, { ...options, headers });
}

function renderHealth(health) {
  const hasError = Number(health.today_errors || 0) > 0 || Boolean(health.last_error);
  adminElements.healthStatus.textContent = hasError ? "Needs review" : "Operational";
  const cards = [
    ["Enabled", `${health.enabled_preferences || 0} of ${health.total_preferences || 0}`],
    ["Delivered today", health.today_delivered || 0],
    ["Skipped today", health.today_skipped || 0],
    ["Errors today", health.today_errors || 0],
    ["Last run", health.last_run_id || "None"],
    ["Last success", shortDateTime(health.last_success_at) || "None"],
    ["Last error", health.last_error || "None"],
  ];
  adminElements.health.innerHTML = cards.map(([label, value]) => `
    <article class="admin-health-card">
      <span class="label">${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `).join("");
}

function renderReadiness(readiness) {
  const checks = readiness.checks || [];
  adminElements.readinessStatus.textContent = readiness.ready ? "Ready" : "Needs setup";
  adminElements.readiness.innerHTML = `
    <div class="admin-readiness-grid">
      <div class="admin-health-card">
        <span class="label">Delivery mode</span>
        <strong>${escapeHtml(readiness.delivery_mode || "unknown")}</strong>
      </div>
      <div class="admin-health-card admin-command-card">
        <span class="label">Scheduler command</span>
        <code>${escapeHtml(readiness.scheduler_command || "")}</code>
      </div>
    </div>
    <div class="admin-checks">
      ${checks.map((check) => `
        <article class="admin-check ${check.ok ? "ok" : "warn"}">
          <span>${check.ok ? "Ready" : "Setup"}</span>
          <strong>${escapeHtml(check.label)}</strong>
          <p>${escapeHtml(check.detail)}</p>
        </article>
      `).join("")}
    </div>
  `;
}

function renderAudit(audit) {
  adminElements.auditCount.textContent = `${audit.length} shown`;
  if (!audit.length) {
    adminElements.audit.innerHTML = `<div class="empty">No delivery audit records yet.</div>`;
    return;
  }

  adminElements.audit.innerHTML = `
    <table class="admin-table">
      <thead>
        <tr>
          <th>Time</th>
          <th>Event</th>
          <th>Client</th>
          <th>Mode</th>
          <th>Reason</th>
          <th>Run</th>
        </tr>
      </thead>
      <tbody>
        ${audit.slice().reverse().map((entry) => `
          <tr>
            <td>${escapeHtml(shortDateTime(entry.created_at))}</td>
            <td>${escapeHtml(entry.event || "delivery")}</td>
            <td>${escapeHtml(entry.client_id || "")}</td>
            <td>${escapeHtml(entry.mode || "")}</td>
            <td>${escapeHtml(entry.reason || "")}</td>
            <td>${escapeHtml(entry.run_id || "")}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderPreferences(preferences) {
  adminElements.preferenceCount.textContent = `${preferences.length} saved`;
  if (!preferences.length) {
    adminElements.preferences.innerHTML = `<div class="empty">No digest preferences saved yet.</div>`;
    return;
  }

  adminElements.preferences.innerHTML = `
    <table class="admin-table">
      <thead>
        <tr>
          <th>Client</th>
          <th>Status</th>
          <th>Email</th>
          <th>Time</th>
          <th>Region</th>
          <th>Activity</th>
          <th>Density</th>
          <th>Last Sent</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${preferences.map((preference) => `
          <tr>
            <td>${escapeHtml(preference.client_id)}</td>
            <td>${preference.enabled ? "Enabled" : "Disabled"}</td>
            <td>${escapeHtml(preference.email || "")}</td>
            <td>${escapeHtml(preference.delivery_time || "")}</td>
            <td>${escapeHtml(preference.region || "")}</td>
            <td>${escapeHtml(preference.activity || "")}</td>
            <td>${escapeHtml(preference.density || "")}</td>
            <td>${escapeHtml(preference.last_delivered_for || "")}</td>
            <td>
              <div class="admin-actions">
                <button class="digest-action admin-toggle" type="button" data-client-id="${escapeHtml(preference.client_id)}" data-enabled="${preference.enabled ? "false" : "true"}">
                  ${preference.enabled ? "Disable" : "Enable"}
                </button>
                <button class="digest-action admin-test" type="button" data-client-id="${escapeHtml(preference.client_id)}">Send test</button>
              </div>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
  wirePreferenceActions();
}

function wirePreferenceActions() {
  document.querySelectorAll(".admin-toggle").forEach((button) => {
    button.addEventListener("click", async () => {
      await updatePreference(button.dataset.clientId, button.dataset.enabled === "true");
    });
  });
  document.querySelectorAll(".admin-test").forEach((button) => {
    button.addEventListener("click", async () => {
      await sendPreferenceTest(button.dataset.clientId);
    });
  });
}

async function updatePreference(clientId, enabled) {
  adminElements.actionStatus.textContent = enabled ? "Enabling..." : "Disabling...";
  try {
    const response = await adminFetch(`/api/digest-admin/preferences/${encodeURIComponent(clientId)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const payload = await response.json();
    if (response.status === 401) {
      showAuthPanel(payload.detail || "Admin token is required.");
      throw new Error("Admin token is required");
    }
    if (!response.ok) throw new Error(payload.detail || `API returned ${response.status}`);
    adminElements.actionStatus.textContent = enabled ? "Enabled" : "Disabled";
    await loadDigestAdmin();
  } catch (error) {
    adminElements.actionStatus.textContent = error.message || "Unable to update preference.";
  }
}

async function sendPreferenceTest(clientId) {
  adminElements.actionStatus.textContent = "Sending test...";
  try {
    const response = await adminFetch(`/api/digest-admin/preferences/${encodeURIComponent(clientId)}/test`, {
      method: "POST",
    });
    const payload = await response.json();
    if (response.status === 401) {
      showAuthPanel(payload.detail || "Admin token is required.");
      throw new Error("Admin token is required");
    }
    if (!response.ok) throw new Error(payload.detail || `API returned ${response.status}`);
    adminElements.actionStatus.textContent = payload.results?.[0]?.mode === "outbox" ? "Test queued" : "Test sent";
    await loadDigestAdmin();
  } catch (error) {
    adminElements.actionStatus.textContent = error.message || "Unable to send test.";
  }
}

function shortDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[character]));
}

wireAdminAuth();
loadDigestAdmin();
