const statusElement = document.querySelector("#unsubscribe-status");

async function disableDailyEmail() {
  const params = new URLSearchParams(window.location.search);
  const clientId = params.get("client_id");
  const email = params.get("email");
  const token = params.get("token");

  if (!clientId || !email || !token) {
    statusElement.textContent = "This unsubscribe link is missing required information.";
    return;
  }

  const query = new URLSearchParams({ client_id: clientId, email, token });
  try {
    const response = await fetch(`/api/digest-preferences/unsubscribe?${query.toString()}`, {
      method: "POST",
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to update this preference.");
    }
    statusElement.textContent = payload.disabled
      ? "You will no longer receive the daily TideWindow email for this browser profile."
      : "The daily email preference was not changed.";
  } catch (error) {
    statusElement.textContent = error.message || "Unable to update this preference.";
  }
}

disableDailyEmail();
