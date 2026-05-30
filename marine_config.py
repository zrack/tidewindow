"""Editable station, weather, and zone configuration for TideWindow."""

NOAA_TIDE_STATION = "9446484"     # Tacoma Narrows Bridge
NOAA_CURRENT_STATION = "PCT1601"  # Narrows North

# Coordinates for the Tacoma Narrows / Gig Harbor basin.
WEATHER_LAT = "47.2690"
WEATHER_LON = "-122.5517"

UPDATE_INTERVAL_SECONDS = 360.0
FORECAST_HOURS = 24
FORECAST_MAX_WINDOWS_PER_ACTIVITY = 2
VISIBLE_ZONE_COUNT = 3

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
    },
    "gig_harbor": {
        "title": "INSIDE GIG HARBOR",
        "ui_prefix": "harbor",
        "fixed_current": 0.1,
        "wind_multiplier": 0.6,
    },
    "fox_island": {
        "title": "FOX ISLAND (HALE PASSAGE)",
        "ui_prefix": "fox",
        "current_multiplier": 0.65,
        "wind_multiplier": 1.2,
    },
    "sunrise_beach": {
        "title": "SUNRISE BEACH PARK",
        "ui_prefix": "sunrise",
        "current_multiplier": 0.75,
        "wind_multiplier": 1.15,
    },
    "narrows_park": {
        "title": "NARROWS PARK",
        "ui_prefix": "narrows",
        "current_multiplier": 1.15,
        "wind_multiplier": 1.25,
    },
    "fox_island_pier": {
        "title": "FOX ISLAND FISHING PIER",
        "ui_prefix": "foxpier",
        "current_multiplier": 0.9,
        "wind_multiplier": 1.25,
    },
    "purdy_sand_spit": {
        "title": "PURDY SAND SPIT",
        "ui_prefix": "purdysand",
        "current_multiplier": 1.25,
        "wind_multiplier": 0.9,
    },
    "kopachuck": {
        "title": "KOPACHUCK STATE PARK",
        "ui_prefix": "kopachuck",
        "current_multiplier": 0.45,
        "wind_multiplier": 0.95,
    },
}
