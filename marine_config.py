"""Editable station, weather, and zone configuration for TideWindow."""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().with_name(".env"))

NOAA_TIDE_STATION = "9446484"     # Tacoma Narrows Bridge
NOAA_CURRENT_STATION = "PUG1527"  # The Narrows, 0.3 mi N of bridge (current predictions)

# NWS marine forecast zone for advisories/warnings.
# PZZ135 = Puget Sound and Hood Canal (covers the Tacoma Narrows / Gig Harbor basin).
NWS_MARINE_ZONE = os.getenv("TIDEWINDOW_NWS_ZONE", "PZZ135")
# NWS requires a descriptive User-Agent on all API requests.
NWS_USER_AGENT = os.getenv(
    "TIDEWINDOW_NWS_USER_AGENT",
    "TideWindow/0.1 (marine planning aid; contact via app host)",
)

# Coordinates for the Tacoma Narrows / Gig Harbor basin.
WEATHER_LAT = "47.2690"
WEATHER_LON = "-122.5517"

UPDATE_INTERVAL_SECONDS = 360.0
FORECAST_HOURS = 72
FORECAST_MAX_WINDOWS_PER_ACTIVITY = 4
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

DEFAULT_RISK_TOLERANCE = "standard"
RISK_TOLERANCE_PROFILES = {
    "conservative": {
        "label": "Conservative",
        "safety_threshold_multiplier": 0.85,
    },
    "standard": {
        "label": "Standard",
        "safety_threshold_multiplier": 1.0,
    },
    "aggressive": {
        "label": "Aggressive",
        "safety_threshold_multiplier": 1.15,
    },
}

STATUS_COLORS = {
    "SAFE": "green",
    "OPTIMAL": "green",
    "CAUTION": "yellow",
    "POOR": "yellow",
    "DANGER": "red",
}

GENERIC_KAYAK_RULES = (
    {
        "status": "DANGER",
        "note": "Generic threshold exceeded. Check local conditions closely.",
        "any": (
            {"metric": "wind", "op": ">", "value": 15.0, "risk_adjust": True},
            {"metric": "current", "op": ">", "value": 2.0, "risk_adjust": True},
        ),
    },
    {
        "status": "CAUTION",
        "note": "Generic caution threshold exceeded.",
        "any": (
            {"metric": "wind", "op": ">", "value": 8.0, "risk_adjust": True},
            {"metric": "current", "op": ">", "value": 1.0, "risk_adjust": True},
        ),
    },
    {
        "status": "SAFE",
        "note": "Generic thresholds show manageable conditions.",
    },
)

GENERIC_FISH_RULES = (
    {
        "status": "OPTIMAL",
        "note": "Generic moving-water window looks fishable.",
        "all": (
            {"metric": "current", "op": ">=", "value": 0.5},
            {"metric": "current", "op": "<=", "value": 2.0},
        ),
    },
    {
        "status": "POOR",
        "note": "Generic threshold suggests waiting for better movement.",
    },
)

KAYAK_RULES_BY_ZONE = {
    "purdy_bridge": (
        {
            "status": "DANGER",
            "note": "Purdy spit current is acting like a river. Do not paddle.",
            "all": ({"metric": "current", "op": ">", "value": 2.0, "risk_adjust": True},),
        },
        {
            "status": "CAUTION",
            "note": "Strong pull under the bridge. Stay near the edges.",
            "all": ({"metric": "current", "op": ">", "value": 1.0, "risk_adjust": True},),
        },
        {
            "status": "SAFE",
            "note": "Near slack water. Safe to transit under bridge.",
        },
    ),
    "gig_harbor": (
        {
            "status": "CAUTION",
            "note": "High winds creating chop inside harbor.",
            "all": ({"metric": "wind", "op": ">", "value": 15.0, "risk_adjust": True},),
        },
        {
            "status": "SAFE",
            "note": "Enclosed water. Ideal for casual paddling.",
        },
    ),
    "fox_island": (
        {
            "status": "DANGER",
            "note": "High exposure. Dangerous fetch and currents.",
            "any": (
                {"metric": "wind", "op": ">", "value": 12.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 2.0, "risk_adjust": True},
            ),
        },
        {
            "status": "CAUTION",
            "note": "Moderate chop in Hale Passage. Stay close to shore.",
            "any": (
                {"metric": "wind", "op": ">", "value": 8.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 1.0, "risk_adjust": True},
            ),
        },
        {
            "status": "SAFE",
            "note": "Good conditions around Fox Island bridge and shores.",
        },
    ),
    "sunrise_beach": (
        {
            "status": "DANGER",
            "note": "Open shoreline exposure. Avoid marginal paddling windows.",
            "any": (
                {"metric": "wind", "op": ">", "value": 14.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 1.8, "risk_adjust": True},
            ),
        },
        {
            "status": "CAUTION",
            "note": "Exposed beach. Watch for chop and landing conditions.",
            "any": (
                {"metric": "wind", "op": ">", "value": 9.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 1.0, "risk_adjust": True},
            ),
        },
        {
            "status": "SAFE",
            "note": "Manageable shoreline conditions near Sunrise Beach.",
        },
    ),
    "narrows_park": (
        {
            "status": "DANGER",
            "note": "Narrows exposure can build fast. Strong current risk.",
            "any": (
                {"metric": "current", "op": ">", "value": 1.8, "risk_adjust": True},
                {"metric": "wind", "op": ">", "value": 12.0, "risk_adjust": True},
            ),
        },
        {
            "status": "CAUTION",
            "note": "Stay alert near Narrows Park; conditions can change quickly.",
            "any": (
                {"metric": "current", "op": ">", "value": 0.8, "risk_adjust": True},
                {"metric": "wind", "op": ">", "value": 8.0, "risk_adjust": True},
            ),
        },
        {
            "status": "SAFE",
            "note": "Lower current window along the Narrows shoreline.",
        },
    ),
    "fox_island_pier": (
        {
            "status": "DANGER",
            "note": "Pier area is exposed to fetch and current.",
            "any": (
                {"metric": "wind", "op": ">", "value": 12.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 2.0, "risk_adjust": True},
            ),
        },
        {
            "status": "CAUTION",
            "note": "Use caution around pier structure and wind chop.",
            "any": (
                {"metric": "wind", "op": ">", "value": 8.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 1.0, "risk_adjust": True},
            ),
        },
        {
            "status": "SAFE",
            "note": "Reasonable conditions around the fishing pier.",
        },
    ),
    "purdy_sand_spit": (
        {
            "status": "DANGER",
            "note": "Strong flow near the spit and bridge. Avoid paddling.",
            "all": ({"metric": "current", "op": ">", "value": 2.0, "risk_adjust": True},),
        },
        {
            "status": "CAUTION",
            "note": "Watch the spit edges and bridge current.",
            "any": (
                {"metric": "current", "op": ">", "value": 1.0, "risk_adjust": True},
                {"metric": "wind", "op": ">", "value": 12.0, "risk_adjust": True},
            ),
        },
        {
            "status": "SAFE",
            "note": "Manageable spit conditions near slack or slower water.",
        },
    ),
    "kopachuck": (
        {
            "status": "DANGER",
            "note": "Henderson Bay exposure can create rough landings.",
            "any": (
                {"metric": "wind", "op": ">", "value": 15.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 1.8, "risk_adjust": True},
            ),
        },
        {
            "status": "CAUTION",
            "note": "Moderate exposure off Kopachuck. Mind beach landing.",
            "any": (
                {"metric": "wind", "op": ">", "value": 9.0, "risk_adjust": True},
                {"metric": "current", "op": ">", "value": 1.0, "risk_adjust": True},
            ),
        },
        {
            "status": "SAFE",
            "note": "Good sheltered-to-moderate beach conditions.",
        },
    ),
}

FISH_RULES_BY_ZONE = {
    "purdy_bridge": (
        {
            "status": "DANGER",
            "note": "Current too fast to safely wade the spit.",
            "all": ({"metric": "current", "op": ">", "value": 3.0, "risk_adjust": True},),
        },
        {
            "status": "OPTIMAL",
            "note": "Current is ripping bait through the channel. Cast into the seams.",
            "all": (
                {"metric": "current", "op": ">=", "value": 1.0},
                {"metric": "current", "op": "<=", "value": 3.0},
            ),
        },
        {
            "status": "POOR",
            "note": "Slack water. Sea-run cutthroat are likely inactive.",
        },
    ),
    "gig_harbor": (
        {
            "status": "OPTIMAL",
            "note": "High tide pushing bait into the harbor estuaries.",
            "all": ({"metric": "tide", "op": ">", "value": 8.0},),
        },
        {
            "status": "POOR",
            "note": "Low water. Fish have moved out to deeper Narrows structure.",
        },
    ),
    "fox_island": (
        {
            "status": "OPTIMAL",
            "note": "Good current sweeping the Hale Passage drop-offs.",
            "all": (
                {"metric": "current", "op": ">=", "value": 0.5},
                {"metric": "current", "op": "<=", "value": 2.0},
            ),
        },
        {
            "status": "CAUTION",
            "note": "Wait for moving water to trigger feeding.",
        },
    ),
    "sunrise_beach": (
        {
            "status": "OPTIMAL",
            "note": "Good moving water along Sunrise Beach structure.",
            "all": (
                {"metric": "current", "op": ">=", "value": 0.4},
                {"metric": "current", "op": "<=", "value": 1.8},
            ),
        },
        {
            "status": "POOR",
            "note": "Look for more current along the shoreline.",
        },
    ),
    "narrows_park": (
        {
            "status": "OPTIMAL",
            "note": "Current is moving bait along the Narrows shoreline.",
            "all": (
                {"metric": "current", "op": ">=", "value": 0.5},
                {"metric": "current", "op": "<=", "value": 1.8},
            ),
        },
        {
            "status": "DANGER",
            "note": "Too much current for comfortable shore casting.",
            "all": ({"metric": "current", "op": ">", "value": 2.5, "risk_adjust": True},),
        },
        {
            "status": "CAUTION",
            "note": "Wait for a stronger but manageable current push.",
        },
    ),
    "fox_island_pier": (
        {
            "status": "OPTIMAL",
            "note": "Good current around pier structure and drop-offs.",
            "all": (
                {"metric": "current", "op": ">=", "value": 0.5},
                {"metric": "current", "op": "<=", "value": 2.0},
            ),
        },
        {
            "status": "CAUTION",
            "note": "Better when water is moving around the pier.",
        },
    ),
    "purdy_sand_spit": (
        {
            "status": "OPTIMAL",
            "note": "Moving water along the spit can concentrate bait.",
            "all": (
                {"metric": "current", "op": ">=", "value": 1.0},
                {"metric": "current", "op": "<=", "value": 2.8},
            ),
        },
        {
            "status": "DANGER",
            "note": "Current too fast near the spit and bridge.",
            "all": ({"metric": "current", "op": ">", "value": 3.0, "risk_adjust": True},),
        },
        {
            "status": "POOR",
            "note": "Slack water around the spit is often less productive.",
        },
    ),
    "kopachuck": (
        {
            "status": "OPTIMAL",
            "note": "Higher water and movement can work the beach edge.",
            "all": (
                {"metric": "tide", "op": ">", "value": 8.0},
                {"metric": "current", "op": ">", "value": 0.3},
            ),
        },
        {
            "status": "POOR",
            "note": "Wait for higher water or more beach movement.",
        },
    ),
}

ZONES = {
    "purdy_bridge": {
        "title": "PURDY BRIDGE (HENDERSON BAY)",
        "ui_prefix": "purdy",
        "current_multiplier": 1.4,
        "wind_multiplier": 0.8,
        "wind_exposure_bearing": 180,
        "lat": 47.389,
        "lon": -122.625,
    },
    "gig_harbor": {
        "title": "INSIDE GIG HARBOR",
        "ui_prefix": "harbor",
        "fixed_current": 0.1,
        "wind_multiplier": 0.6,
        "wind_exposure_bearing": 200,
        "lat": 47.331,
        "lon": -122.582,
    },
    "fox_island": {
        "title": "FOX ISLAND (HALE PASSAGE)",
        "ui_prefix": "fox",
        "current_multiplier": 0.65,
        "wind_multiplier": 1.2,
        "wind_exposure_bearing": 210,
        "lat": 47.261,
        "lon": -122.605,
    },
    "sunrise_beach": {
        "title": "SUNRISE BEACH PARK",
        "ui_prefix": "sunrise",
        "current_multiplier": 0.75,
        "wind_multiplier": 1.15,
        "wind_exposure_bearing": 45,
        "lat": 47.351,
        "lon": -122.513,
    },
    "narrows_park": {
        "title": "NARROWS PARK",
        "ui_prefix": "narrows",
        "current_multiplier": 1.15,
        "wind_multiplier": 1.25,
        "wind_exposure_bearing": 220,
        "lat": 47.280,
        "lon": -122.548,
    },
    "fox_island_pier": {
        "title": "FOX ISLAND FISHING PIER",
        "ui_prefix": "foxpier",
        "current_multiplier": 0.9,
        "wind_multiplier": 1.25,
        "wind_exposure_bearing": 220,
        "lat": 47.252,
        "lon": -122.629,
    },
    "purdy_sand_spit": {
        "title": "PURDY SAND SPIT",
        "ui_prefix": "purdysand",
        "current_multiplier": 1.25,
        "wind_multiplier": 0.9,
        "wind_exposure_bearing": 180,
        "lat": 47.386,
        "lon": -122.629,
    },
    "kopachuck": {
        "title": "KOPACHUCK STATE PARK",
        "ui_prefix": "kopachuck",
        "current_multiplier": 0.45,
        "wind_multiplier": 0.95,
        "wind_exposure_bearing": 190,
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
        "wind_exposure_bearing": 180,
        "lat": 47.296,
        "lon": -122.592,
    },
    "horsehead_bay": {
        "title": "HORSEHEAD BAY",
        "ui_prefix": "horsehead",
        "current_multiplier": 0.35,
        "wind_multiplier": 0.85,
        "wind_exposure_bearing": 170,
        "lat": 47.313,
        "lon": -122.703,
    },
    "raft_island": {
        "title": "RAFT ISLAND",
        "ui_prefix": "raft",
        "current_multiplier": 0.55,
        "wind_multiplier": 1.0,
        "wind_exposure_bearing": 190,
        "lat": 47.331,
        "lon": -122.668,
    },
    "rosedale_beach": {
        "title": "ROSEDALE GARDENS BEACH",
        "ui_prefix": "rosedale",
        "current_multiplier": 0.4,
        "wind_multiplier": 0.8,
        "wind_exposure_bearing": 180,
        "lat": 47.334,
        "lon": -122.616,
    },
    "point_fosdick": {
        "title": "POINT FOSDICK SHORELINE",
        "ui_prefix": "fosdick",
        "current_multiplier": 0.5,
        "wind_multiplier": 1.0,
        "wind_exposure_bearing": 220,
        "lat": 47.299,
        "lon": -122.579,
    },
}

ALL_ZONES = {
    **ZONES,
    **OPTIONAL_ZONES,
}
