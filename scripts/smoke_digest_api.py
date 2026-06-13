"""Smoke-test digest delivery API routes against a running local server."""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


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
    run_due = request("/api/digest-deliveries/run?now=2026-06-13T06%3A01%3A00", "POST")

    assert saved["preferences"]["email"] == "smoke@example.com", saved
    assert loaded["preferences"]["activity"] == "Kayak", loaded
    assert test_delivery["results"][0]["delivered"], test_delivery
    assert any(result["client_id"] == client_id for result in run_due["results"]), run_due

    print("digest api smoke ok")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach {BASE_URL}: {exc}") from exc
