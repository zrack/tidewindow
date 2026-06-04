#!/usr/bin/env python3
"""Find the nearest NOAA current-prediction stations to a coordinate.

The station configured in marine_config (PCT1601) is not a valid NOAA current
station, so current telemetry has always fallen back to seed data. This script
queries NOAA's station metadata API for real current-prediction stations and
lists the closest ones to the Gig Harbor / Tacoma Narrows basin so you can pick
a valid replacement for NOAA_CURRENT_STATION.

Usage:
    python3 scripts/find_current_station.py [LAT] [LON]

Defaults to the WEATHER_LAT/WEATHER_LON in marine_config (47.2690, -122.5517).
Standard library only.
"""

import json
import math
import sys
import urllib.request

MDAPI_URL = (
    "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
    "?type=currentpredictions&units=english"
)
DEFAULT_LAT = 47.2690
DEFAULT_LON = -122.5517


def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    radius = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return radius * 2 * math.asin(math.sqrt(a))


def main() -> int:
    lat = float(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LAT
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_LON
    print(f"Finding current-prediction stations near ({lat}, {lon})\n")

    try:
        with urllib.request.urlopen(MDAPI_URL, timeout=15.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - diagnostic script
        print(f"Request failed: {error}")
        return 1

    stations = payload.get("stations", [])
    ranked = []
    for station in stations:
        try:
            distance = haversine_miles(lat, lon, float(station["lat"]), float(station["lng"]))
        except (KeyError, TypeError, ValueError):
            continue
        ranked.append((distance, station))

    ranked.sort(key=lambda entry: entry[0])
    if not ranked:
        print("No current-prediction stations returned.")
        return 1

    print(f"{'dist(mi)':>9}  {'id':<10} name")
    print("-" * 60)
    for distance, station in ranked[:10]:
        print(f"{distance:9.1f}  {station.get('id', '?'):<10} {station.get('name', '')}")

    nearest = ranked[0][1]
    print(
        "\nClosest match: "
        f"{nearest.get('id')} — {nearest.get('name')}\n"
        "Update marine_config.py:  NOAA_CURRENT_STATION = "
        f"\"{nearest.get('id')}\"\n"
        "Then re-run: python3 scripts/check_current_station.py "
        f"{nearest.get('id')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
