"""Editable station, weather, and zone configuration for TideWindow."""

import os

from dotenv import load_dotenv


load_dotenv()

NOAA_TIDE_STATION = "9446484"     # Tacoma Narrows Bridge
NOAA_CURRENT_STATION = "PUG1527"  # The Narrows, 0.3 mi N of bridge (current predictions)

# Coordinates for the Tacoma Narrows / Gig Harbor basin.
WEATHER_LAT = "47.2690"
WEATHER_LON = "-122.5517"

UPDATE_INTERVAL_SECONDS = 360.0
FORECAST_HOURS = 24
FORECAST_MAX_WINDOWS_PER_ACTIVITY = 2
VISIBLE_ZONE_COUNT = 3

WEB_APP_NAME = os.getenv("TIDEWINDOW_WEB_APP_NAME", "TideWindow")
WEB_REFRESH_INTERVAL_SECONDS = float(os.getenv("TIDEWINDOW_WEB_REFRESH_SECONDS", "300"))

# Converts hourly tide movement into a rough current estimate for planning windows.
# The result is intentionally labeled as derived forecast data in the UI.
TIDE_SLOPE_TO_CURRENT_KNOTS = 0.75

DEFAULT_WIND_KNOTS = 6.5
SEEDED_TIDE_FEET = 5.4
SEEDED_CURRENT_KNOTS = 1.85
SEEDED_CURRENT_DIRECTION = 140.0

ZONES = {
    "purdy_bridge": {
        "title": "PURDY BRIDGE (HENDERSON BAY)",
        "ui_prefix": "purdy",
        "current_multiplier": 1.4,
        "wind_multiplier": 0.8,
        "lat": 47.389,
        "lon": -122.625,
    },
    "gig_harbor": {
        "title": "INSIDE GIG HARBOR",
        "ui_prefix": "harbor",
        "fixed_current": 0.1,
        "wind_multiplier": 0.6,
        "lat": 47.331,
        "lon": -122.582,
    },
    "fox_island": {
        "title": "FOX ISLAND (HALE PASSAGE)",
        "ui_prefix": "fox",
        "current_multiplier": 0.65,
        "wind_multiplier": 1.2,
        "lat": 47.261,
        "lon": -122.605,
    },
    "sunrise_beach": {
        "title": "SUNRISE BEACH PARK",
        "ui_prefix": "sunrise",
        "current_multiplier": 0.75,
        "wind_multiplier": 1.15,
        "lat": 47.351,
        "lon": -122.513,
    },
    "narrows_park": {
        "title": "NARROWS PARK",
        "ui_prefix": "narrows",
        "current_multiplier": 1.15,
        "wind_multiplier": 1.25,
        "lat": 47.280,
        "lon": -122.548,
    },
    "fox_island_pier": {
        "title": "FOX ISLAND FISHING PIER",
        "ui_prefix": "foxpier",
        "current_multiplier": 0.9,
        "wind_multiplier": 1.25,
        "lat": 47.252,
        "lon": -122.629,
    },
    "purdy_sand_spit": {
        "title": "PURDY SAND SPIT",
        "ui_prefix": "purdysand",
        "current_multiplier": 1.25,
        "wind_multiplier": 0.9,
        "lat": 47.386,
        "lon": -122.629,
    },
    "kopachuck": {
        "title": "KOPACHUCK STATE PARK",
        "ui_prefix": "kopachuck",
        "current_multiplier": 0.45,
        "wind_multiplier": 0.95,
        "lat": 47.307,
        "lon": -122.680,
    },
}

OPTIONAL_ZONES = {
    "wollochet_bay": {
        "title": "WOLLOCHET BAY",
        "ui_prefix": "wollochet",
        "fixed_current": 0.2,
        "wind_multiplier": 0.75,
        "lat": 47.296,
        "lon": -122.592,
    },
    "horsehead_bay": {
        "title": "HORSEHEAD BAY",
        "ui_prefix": "horsehead",
        "current_multiplier": 0.35,
        "wind_multiplier": 0.85,
        "lat": 47.313,
        "lon": -122.703,
    },
    "raft_island": {
        "title": "RAFT ISLAND",
        "ui_prefix": "raft",
        "current_multiplier": 0.55,
        "wind_multiplier": 1.0,
        "lat": 47.331,
        "lon": -122.668,
    },
    "rosedale_beach": {
        "title": "ROSEDALE GARDENS BEACH",
        "ui_prefix": "rosedale",
        "current_multiplier": 0.4,
        "wind_multiplier": 0.8,
        "lat": 47.334,
        "lon": -122.616,
    },
    "point_fosdick": {
        "title": "POINT FOSDICK SHORELINE",
        "ui_prefix": "fosdick",
        "current_multiplier": 0.5,
        "wind_multiplier": 1.0,
        "lat": 47.299,
        "lon": -122.579,
    },
}

ALL_ZONES = {
    **ZONES,
    **OPTIONAL_ZONES,
}
