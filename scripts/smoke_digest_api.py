"""Smoke-test digest delivery API routes against a running local server."""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digest_delivery import sign_unsubscribe_token


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"


def request(path: str, method: str = "GET", body: dict | None = None) -> dict:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    client_id = f"smoke-{int(time.time())}"
    query = urllib.parse.urlencode({"client_id": client_id})
    preferences = {
        "enabled": True,
        "email": "smoke@example.com",
        "delivery_time": "06:00",
        "region": "gig_harbor",
        "activity": "Kayak",
        "risk": "standard",
        "density": "compact",
    }

    saved = request(f"/api/digest-preferences?{query}", "POST", preferences)
    loaded = request(f"/api/digest-preferences?{query}")
    test_delivery = request(f"/api/digest-deliveries/test?{query}", "POST")
    run_query = {
        "now": "2026-06-13T06:01:00",
        "run_id": "smoke-run",
    }
    if os.getenv("TIDEWINDOW_SCHEDULER_TOKEN"):
        run_query["scheduler_token"] = os.environ["TIDEWINDOW_SCHEDULER_TOKEN"]
    run_due = request(f"/api/digest-deliveries/run?{urllib.parse.urlencode(run_query)}", "POST")
    audit = request("/api/digest-deliveries/audit?limit=10")
    unsubscribe_query = urllib.parse.urlencode({
        "client_id": client_id,
        "email": "smoke@example.com",
        "token": sign_unsubscribe_token(client_id, "smoke@example.com"),
    })
    unsubscribed = request(f"/api/digest-preferences/unsubscribe?{unsubscribe_query}", "POST")

    assert saved["preferences"]["email"] == "smoke@example.com", saved
    assert loaded["preferences"]["activity"] == "Kayak", loaded
    assert test_delivery["results"][0]["delivered"], test_delivery
    assert run_due["run_id"] == "smoke-run", run_due
    assert any(result["client_id"] == client_id for result in run_due["results"]), run_due
    assert any(entry["client_id"] == client_id for entry in audit["audit"]), audit
    assert unsubscribed["disabled"], unsubscribed

    print("digest api smoke ok")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach {BASE_URL}: {exc}") from exc
