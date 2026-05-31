"""Editable station, weather, and zone configuration for TideWindow."""

import os

from dotenv import load_dotenv


load_dotenv()

NOAA_TIDE_STATION = "9446484"     # Tacoma Narrows Bridge
NOAA_CURRENT_STATION = "PCT1601"  # Narrows North

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
        "map_x": 46,
        "map_y": 30,
    },
    "gig_harbor": {
        "title": "INSIDE GIG HARBOR",
        "ui_prefix": "harbor",
        "fixed_current": 0.1,
        "wind_multiplier": 0.6,
        "map_x": 56,
        "map_y": 42,
    },
    "fox_island": {
        "title": "FOX ISLAND (HALE PASSAGE)",
        "ui_prefix": "fox",
        "current_multiplier": 0.65,
        "wind_multiplier": 1.2,
        "map_x": 42,
        "map_y": 70,
    },
    "sunrise_beach": {
        "title": "SUNRISE BEACH PARK",
        "ui_prefix": "sunrise",
        "current_multiplier": 0.75,
        "wind_multiplier": 1.15,
        "map_x": 72,
        "map_y": 31,
    },
    "narrows_park": {
        "title": "NARROWS PARK",
        "ui_prefix": "narrows",
        "current_multiplier": 1.15,
        "wind_multiplier": 1.25,
        "map_x": 75,
        "map_y": 77,
    },
    "fox_island_pier": {
        "title": "FOX ISLAND FISHING PIER",
        "ui_prefix": "foxpier",
        "current_multiplier": 0.9,
        "wind_multiplier": 1.25,
        "map_x": 34,
        "map_y": 61,
    },
    "purdy_sand_spit": {
        "title": "PURDY SAND SPIT",
        "ui_prefix": "purdysand",
        "current_multiplier": 1.25,
        "wind_multiplier": 0.9,
        "map_x": 35,
        "map_y": 21,
    },
    "kopachuck": {
        "title": "KOPACHUCK STATE PARK",
        "ui_prefix": "kopachuck",
        "current_multiplier": 0.45,
        "wind_multiplier": 0.95,
        "map_x": 24,
        "map_y": 46,
    },
}

OPTIONAL_ZONES = {
    "wollochet_bay": {
        "title": "WOLLOCHET BAY",
        "ui_prefix": "wollochet",
        "fixed_current": 0.2,
        "wind_multiplier": 0.75,
        "map_x": 47,
        "map_y": 53,
    },
    "horsehead_bay": {
        "title": "HORSEHEAD BAY",
        "ui_prefix": "horsehead",
        "current_multiplier": 0.35,
        "wind_multiplier": 0.85,
        "map_x": 18,
        "map_y": 36,
    },
    "raft_island": {
        "title": "RAFT ISLAND",
        "ui_prefix": "raft",
        "current_multiplier": 0.55,
        "wind_multiplier": 1.0,
        "map_x": 30,
        "map_y": 38,
    },
    "rosedale_beach": {
        "title": "ROSEDALE GARDENS BEACH",
        "ui_prefix": "rosedale",
        "current_multiplier": 0.4,
        "wind_multiplier": 0.8,
        "map_x": 48,
        "map_y": 34,
    },
    "point_fosdick": {
        "title": "POINT FOSDICK SHORELINE",
        "ui_prefix": "fosdick",
        "current_multiplier": 0.5,
        "wind_multiplier": 1.0,
        "map_x": 64,
        "map_y": 58,
    },
}

ALL_ZONES = {
    **ZONES,
    **OPTIONAL_ZONES,
}
