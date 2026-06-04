#!/usr/bin/env python3
"""Diagnose whether a NOAA current station serves real-time data.

TideWindow's telemetry asks NOAA for the real-time ``currents`` product. Some
stations (harmonic prediction stations, e.g. those with a ``PCT`` prefix) have
no real-time sensor and return an empty payload, which means "Current: live" is
really seed/predicted data. This script checks both the real-time product and
the ``currents_predictions`` fallback so you can confirm what your station
actually provides.

Usage:
    python3 scripts/check_current_station.py [STATION_ID]

Defaults to PCT1601 (the station in marine_config). Uses only the standard
library, so it runs without installing the project's dependencies.
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime

NOAA_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
DEFAULT_STATION = "PCT1601"


def fetch_json(params: dict, timeout: float = 10.0) -> dict:
    url = f"{NOAA_URL}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_realtime(station: str) -> bool:
    print(f"\n[1] Real-time currents (product=currents) for {station}")
    try:
        payload = fetch_json(
            {
                "range": "1",
                "station": station,
                "product": "currents",
                "time_zone": "lst_ldt",
                "units": "english",
                "format": "json",
            }
        )
    except Exception as error:  # noqa: BLE001 - diagnostic script
        print(f"    request failed: {error}")
        return False

    if isinstance(payload, dict) and payload.get("error"):
        print(f"    NOAA error: {payload['error'].get('message', payload['error'])}")
        return False

    data = payload.get("data", []) if isinstance(payload, dict) else []
    if not data:
        print("    no real-time data points returned (station likely has no sensor)")
        return False

    latest = data[-1]
    print(f"    OK: {len(data)} point(s); latest s={latest.get('s')} kt, d={latest.get('d')}deg at {latest.get('t')}")
    return True


def check_predictions(station: str) -> bool:
    print(f"\n[2] Current predictions (product=currents_predictions) for {station}")
    try:
        payload = fetch_json(
            {
                "date": "today",
                "station": station,
                "product": "currents_predictions",
                "time_zone": "lst_ldt",
                "interval": "30",
                "units": "english",
                "vel_type": "speed_dir",
                "format": "json",
            }
        )
    except Exception as error:  # noqa: BLE001 - diagnostic script
        print(f"    request failed: {error}")
        return False

    if isinstance(payload, dict) and payload.get("error"):
        print(f"    NOAA error: {payload['error'].get('message', payload['error'])}")
        return False

    points = payload.get("current_predictions", {}).get("cp", []) if isinstance(payload, dict) else []
    if not points:
        print("    no prediction points returned")
        return False

    now = datetime.now()
    parsed = []
    for item in points:
        try:
            point_time = datetime.strptime(item["Time"], "%Y-%m-%d %H:%M")
        except (KeyError, ValueError, TypeError):
            continue
        speed = item.get("Speed", item.get("Velocity_Major"))
        parsed.append((point_time, speed, item.get("Direction")))

    if not parsed:
        print("    points returned but could not be parsed")
        return False

    nearest = min(parsed, key=lambda entry: abs((entry[0] - now).total_seconds()))
    print(f"    OK: {len(parsed)} point(s); nearest-to-now ~{nearest[1]} kt @ {nearest[2]}deg at {nearest[0]}")
    return True


def main() -> int:
    station = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STATION
    print(f"Checking NOAA current station: {station}")

    realtime_ok = check_realtime(station)
    predictions_ok = check_predictions(station)

    print("\nVerdict:")
    if realtime_ok:
        print("  Real-time currents work. 'Current: live' is accurate.")
    elif predictions_ok:
        print("  No real-time currents, but predictions work.")
        print("  TideWindow now labels this current data 'predicted' (the #4 fix). Working as intended.")
    else:
        print("  Neither real-time nor predicted currents are available for this station.")
        print("  Consider choosing a different current station in marine_config.py.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
