"""Region and spot selection helpers for TideWindow.

This module is the first step toward city/place based selection. It keeps the
current Gig Harbor dashboard behavior intact while introducing data structures
that can later support places such as Port Orchard or Aberdeen.
"""

import re
from copy import deepcopy

from marine_config import (
    ALL_ZONES,
    NOAA_CURRENT_STATION,
    NOAA_TIDE_STATION,
    NWS_MARINE_ZONE,
    OPTIONAL_ZONES,
    WEATHER_LAT,
    WEATHER_LON,
    ZONES,
)


DEFAULT_REGION_ID = "gig_harbor"

TIDE_STATION_METADATA = {
    "9445958": {"name": "Bremerton", "type": "R"},
    "9446484": {"name": "Tacoma", "type": "R"},
    "9446291": {"name": "Wauna, Carr Inlet", "type": "R"},
    "9446281": {"name": "Allyn, Case Inlet", "type": "S"},
    "9446804": {"name": "Sandy Point Anderson Island", "type": "R"},
    "9446714": {"name": "Steilacoom, Cormorant Passage", "type": "S"},
    "9446807": {"name": "Budd Inlet, Olympia Shoal", "type": "R"},
    "9445478": {"name": "Union, Hood Canal", "type": "R"},
    "9445441": {"name": "Lynch Cove Dock", "type": "S"},
    "9445388": {"name": "Ayock Point", "type": "S"},
    "9445326": {"name": "Triton Head", "type": "S"},
    "9441187": {"name": "Aberdeen", "type": "R"},
}
CURRENT_STATION_METADATA = {
    "PUG1510": {"name": "Port Washington Narrows, Warren Ave. Bridge", "type": "H"},
    "PUG1514": {"name": "Rich Passage, West end", "type": "H"},
    "PUG1527": {"name": "The Narrows, 0.3 miles North of Bridge", "type": "H"},
    "PUG1530": {"name": "Hale Passage, West end", "type": "H"},
    "PUG1548": {"name": "Pickering Passage, North end", "type": "H"},
    "PUG1535": {"name": "Balch Passage, NE of Eagle Island", "type": "H"},
    "PUG1532": {"name": "Steilacoom, 0.8 miles North of", "type": "H"},
    "PUG1540": {"name": "Budd Inlet Entrance", "type": "H"},
    "PUG1601": {"name": "Hazel Point, Hood Canal", "type": "H"},
    "PUG1602": {"name": "South Point, Hood Canal", "type": "H"},
    "PCT1596": {"name": "Chinom Point, Hood Canal", "type": "S"},
    "ACT8496": {"name": "Grays Harbor Entrance", "type": "S"},
}


def describe_provider_context(provider_context: dict) -> dict:
    """Adds station names, NOAA station types, and confidence guidance."""
    context = deepcopy(provider_context)
    tide_meta = TIDE_STATION_METADATA.get(context.get("tide_station"), {})
    current_meta = CURRENT_STATION_METADATA.get(context.get("current_station"), {})
    context["tide_station_name"] = tide_meta.get("name", context.get("tide_station"))
    context["tide_station_type"] = tide_meta.get("type", "unknown")
    context["current_station_name"] = current_meta.get("name", context.get("current_station"))
    context["current_station_type"] = current_meta.get("type", "unknown")
    context["provider_strategy"] = provider_strategy(context)
    context["provider_confidence"] = provider_confidence(context)
    return context


def provider_strategy(provider_context: dict) -> dict:
    """Builds a displayable provider priority/fallback plan for a region."""
    profile = provider_context.get("provider_profile", "station_backed")
    tide_priority = [
        _tide_priority_item(provider_context, "Primary tide"),
        *[
            _tide_priority_item({**provider_context, "tide_station": station}, "Backup tide")
            for station in provider_context.get("backup_tide_stations", ())
        ],
    ]
    current_priority = [
        _current_priority_item(provider_context, "Primary current"),
        *[
            _current_priority_item({**provider_context, **station}, "Backup current")
            for station in provider_context.get("backup_current_stations", ())
        ],
        {
            "label": "Fallback current",
            "mode": "derived",
            "name": "Derived from tide slope",
            "type": "derived",
            "note": "Used when current predictions are unavailable or outside the forecast window.",
        },
    ]

    profile_labels = {
        "station_backed": "Station-backed",
        "subordinate_station": "Subordinate station",
        "sparse_current": "Sparse current coverage",
        "river_bar_influenced": "River/bar influenced",
        "derived_current_only": "Derived-current fallback",
    }
    return {
        "profile": profile,
        "headline": profile_labels.get(profile, "Station strategy"),
        "tide_priority": tide_priority,
        "current_priority": current_priority,
        "warnings": tuple(provider_context.get("provider_warnings", ())),
    }


def _tide_priority_item(provider_context: dict, label: str) -> dict:
    station = provider_context.get("tide_station")
    meta = TIDE_STATION_METADATA.get(station, {})
    return {
        "label": label,
        "station": station,
        "name": meta.get("name", station),
        "type": meta.get("type", "unknown"),
    }


def _current_priority_item(provider_context: dict, label: str) -> dict:
    station = provider_context.get("current_station")
    meta = CURRENT_STATION_METADATA.get(station, {})
    return {
        "label": label,
        "station": station,
        "name": meta.get("name", station),
        "type": meta.get("type", "unknown"),
        "bin": provider_context.get("current_bin"),
        "depth_ft": provider_context.get("current_bin_depth_ft"),
    }


def provider_confidence(provider_context: dict) -> dict:
    """Rates provider fit using NOAA tide/current station type metadata."""
    tide_type = provider_context.get("tide_station_type", "unknown")
    current_type = provider_context.get("current_station_type", "unknown")
    profile = provider_context.get("provider_strategy", {}).get(
        "profile",
        provider_context.get("provider_profile", "station_backed"),
    )
    if profile == "derived_current_only":
        return {
            "level": "Low",
            "color": "red",
            "label": "Derived current only",
            "note": "No station-quality current prediction is configured; current scoring is derived from tide movement.",
            "reasons": ("Derived current only",),
        }
    if profile == "river_bar_influenced":
        return {
            "level": "Medium",
            "color": "yellow",
            "label": "River/bar influenced",
            "note": "Tide and current stations are usable, but river flow, swell, and bar conditions can override simple scoring.",
            "reasons": ("River flow can shift timing", "Bar and swell require separate checks"),
        }
    if profile == "sparse_current":
        return {
            "level": "Medium",
            "color": "yellow",
            "label": "Sparse current coverage",
            "note": "Uses harmonic current predictions, but coverage is sparse; confidence varies by spot distance from the station.",
            "reasons": ("Harmonic current station is not local to every spot",),
        }
    if current_type == "W":
        return {
            "level": "Low",
            "color": "red",
            "label": "Weak current station",
            "note": "Current station is weak/variable; treat current scoring as approximate.",
            "reasons": ("Weak/variable current station",),
        }
    if "unknown" in {tide_type, current_type}:
        return {
            "level": "Low",
            "color": "red",
            "label": "Incomplete station metadata",
            "note": "Station type metadata is incomplete for this region.",
            "reasons": ("Station metadata incomplete",),
        }
    if tide_type == "S" or current_type == "S":
        return {
            "level": "Medium",
            "color": "yellow",
            "label": "Subordinate station fit",
            "note": "Uses a subordinate NOAA station for part of the provider context.",
            "reasons": ("Subordinate NOAA station",),
        }
    return {
        "level": "High",
        "color": "green",
        "label": "High station fit",
        "note": "Uses station-backed tide data and harmonic NOAA current predictions.",
        "reasons": ("Reference tide station", "Harmonic current prediction"),
    }


BREMERTON_TIDE_STATION = "9445958"
BREMERTON_PROVIDER_CONTEXT = {
    "tide_station": BREMERTON_TIDE_STATION,
    "current_station": "PUG1510",
    "current_bin": 6,
    "current_bin_depth_ft": 4,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.5650",
    "weather_lon": "-122.6269",
}
PORT_ORCHARD_PROVIDER_CONTEXT = {
    "tide_station": BREMERTON_TIDE_STATION,
    "current_station": "PUG1514",
    "current_bin": 8,
    "current_bin_depth_ft": 12,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.5404",
    "weather_lon": "-122.6362",
}
SILVERDALE_PROVIDER_CONTEXT = {
    "tide_station": BREMERTON_TIDE_STATION,
    "current_station": "PUG1510",
    "current_bin": 6,
    "current_bin_depth_ft": 4,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.6445",
    "weather_lon": "-122.6949",
}
TACOMA_NARROWS_PROVIDER_CONTEXT = {
    "tide_station": "9446484",
    "current_station": "PUG1527",
    "current_bin": 19,
    "current_bin_depth_ft": 23,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.2743",
    "weather_lon": "-122.5453",
}
CARR_INLET_PROVIDER_CONTEXT = {
    "tide_station": "9446291",
    "current_station": "PUG1530",
    "current_bin": 18,
    "current_bin_depth_ft": 14,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.3783",
    "weather_lon": "-122.6340",
}
CASE_INLET_PROVIDER_CONTEXT = {
    "tide_station": "9446281",
    "current_station": "PUG1548",
    "current_bin": 10,
    "current_bin_depth_ft": 19,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.3833",
    "weather_lon": "-122.8230",
}
ANDERSON_ISLAND_PROVIDER_CONTEXT = {
    "tide_station": "9446804",
    "current_station": "PUG1535",
    "current_bin": 16,
    "current_bin_depth_ft": 11,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.1800",
    "weather_lon": "-122.6751",
}
STEILACOOM_PROVIDER_CONTEXT = {
    "tide_station": "9446714",
    "current_station": "PUG1532",
    "current_bin": 16,
    "current_bin_depth_ft": 45,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.1733",
    "weather_lon": "-122.6030",
}
OLYMPIA_BUDD_INLET_PROVIDER_CONTEXT = {
    "tide_station": "9446807",
    "current_station": "PUG1540",
    "current_bin": 10,
    "current_bin_depth_ft": 12,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.0983",
    "weather_lon": "-122.8950",
}
SOUTH_HOOD_CANAL_PROVIDER_CONTEXT = {
    "tide_station": "9445478",
    "current_station": "PUG1601",
    "current_bin": 21,
    "current_bin_depth_ft": 23,
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.3583",
    "weather_lon": "-123.0983",
    "provider_profile": "sparse_current",
    "backup_tide_stations": ("9445441", "9445388"),
    "backup_current_stations": (
        {"current_station": "PUG1602", "current_bin": 42, "current_bin_depth_ft": 43},
        {"current_station": "PCT1596", "current_bin": 1, "current_bin_depth_ft": None},
    ),
    "provider_warnings": (
        "Hazel Point current predictions are useful canal context, but not equally local to Union, Lynch Cove, and Belfair.",
        "Use derived-current fallback and wind exposure conservatively in shallow head-of-canal spots.",
    ),
}
ABERDEEN_PROVIDER_CONTEXT = {
    "tide_station": "9441187",
    "current_station": "ACT8496",
    "current_bin": 1,
    "current_bin_depth_ft": None,
    "nws_zone": "PZZ110",
    "weather_lat": "46.9754",
    "weather_lon": "-123.8157",
    "provider_profile": "river_bar_influenced",
    "provider_warnings": (
        "Chehalis and Wishkah river flow can shift timing and current strength away from tide predictions.",
        "Grays Harbor bar, swell, and coastal wind require separate official checks before ocean-adjacent trips.",
    ),
}

REGIONS = {
    DEFAULT_REGION_ID: {
        "id": DEFAULT_REGION_ID,
        "name": "Gig Harbor",
        "type": "city",
        "center": {"lat": 47.32, "lon": -122.61},
        "default_zoom": 11,
        "default_spot_limit": 13,
        "spot_ids": tuple(ALL_ZONES.keys()),
        "provider_context": {
            "tide_station": NOAA_TIDE_STATION,
            "current_station": NOAA_CURRENT_STATION,
            "current_bin": 19,
            "current_bin_depth_ft": 23,
            "nws_zone": NWS_MARINE_ZONE,
            "weather_lat": WEATHER_LAT,
            "weather_lon": WEATHER_LON,
        },
    },
    "port_orchard": {
        "id": "port_orchard",
        "name": "Port Orchard",
        "type": "city",
        "center": {"lat": 47.5404, "lon": -122.6362},
        "default_zoom": 12,
        "default_spot_limit": 12,
        "spot_ids": (
            "port_orchard_waterfront",
            "port_orchard_marina",
            "annapolis_foot_ferry",
            "blackjack_creek_mouth",
            "ross_point",
            "waterman_pier",
            "manchester_dock",
            "manchester_state_park",
            "southworth_ferry",
            "rich_passage_south_shore",
            "sinclair_inlet_south_shore",
            "long_lake_estuary",
        ),
        "provider_context": PORT_ORCHARD_PROVIDER_CONTEXT,
    },
    "bremerton": {
        "id": "bremerton",
        "name": "Bremerton",
        "type": "city",
        "center": {"lat": 47.5650, "lon": -122.6269},
        "default_zoom": 12,
        "default_spot_limit": 12,
        "spot_ids": (
            "bremerton_marina",
            "bremerton_ferry_terminal",
            "evergreen_rotary_park",
            "manette_bridge",
            "lions_park_bremerton",
            "port_washington_narrows",
            "warren_ave_bridge",
            "illahee_state_park",
            "tracyton_beach",
            "phinney_bay",
            "oyster_bay_bremerton",
            "rocky_point_bremerton",
        ),
        "provider_context": BREMERTON_PROVIDER_CONTEXT,
    },
    "silverdale": {
        "id": "silverdale",
        "name": "Silverdale",
        "type": "city",
        "center": {"lat": 47.6445, "lon": -122.6949},
        "default_zoom": 12,
        "default_spot_limit": 12,
        "spot_ids": (
            "silverdale_waterfront_park",
            "old_town_silverdale",
            "clear_creek_estuary",
            "dyes_inlet_north_shore",
            "barker_creek_mouth",
            "dyes_inlet_east_shore",
            "tracyton_beach",
            "brownsville_marina",
            "illahee_state_park",
            "chico_bay_north",
            "oyster_bay_bremerton",
            "port_washington_narrows",
        ),
        "provider_context": SILVERDALE_PROVIDER_CONTEXT,
    },
    "tacoma_narrows": {
        "id": "tacoma_narrows",
        "name": "Tacoma Narrows",
        "type": "subregion",
        "center": {"lat": 47.2743, "lon": -122.5453},
        "default_zoom": 12,
        "default_spot_limit": 12,
        "spot_ids": (
            "narrows_park",
            "tacoma_narrows_bridge",
            "titlow_beach",
            "salmon_beach",
            "day_island",
            "sunrise_beach",
            "tahlequah_ferry",
            "point_defiance_owen_beach",
            "point_ruston",
            "chambers_creek_mouth",
            "fox_island",
            "point_fosdick",
        ),
        "provider_context": TACOMA_NARROWS_PROVIDER_CONTEXT,
    },
    "carr_inlet": {
        "id": "carr_inlet",
        "name": "Carr Inlet",
        "type": "subregion",
        "center": {"lat": 47.3783, "lon": -122.6340},
        "default_zoom": 11,
        "default_spot_limit": 12,
        "spot_ids": (
            "purdy_bridge",
            "purdy_sand_spit",
            "wauna_waterfront",
            "horsehead_bay",
            "kopachuck",
            "raft_island",
            "vaughn_bay",
            "home_spit",
            "lakebay_marina",
            "cutts_island",
            "rocky_bay",
            "penrose_point",
        ),
        "provider_context": CARR_INLET_PROVIDER_CONTEXT,
    },
    "case_inlet": {
        "id": "case_inlet",
        "name": "Case Inlet",
        "type": "subregion",
        "center": {"lat": 47.3833, "lon": -122.8230},
        "default_zoom": 11,
        "default_spot_limit": 12,
        "spot_ids": (
            "allyn_waterfront",
            "case_inlet_north",
            "vaughn_bay",
            "mcmicken_island",
            "stretch_island",
            "grapeview",
            "jarrell_cove",
            "pickering_passage_north",
            "harstine_bridge",
            "squaxin_passage",
            "rocky_bay",
            "penrose_point",
        ),
        "provider_context": CASE_INLET_PROVIDER_CONTEXT,
    },
    "anderson_island": {
        "id": "anderson_island",
        "name": "Anderson Island",
        "type": "subregion",
        "center": {"lat": 47.1800, "lon": -122.6751},
        "default_zoom": 11,
        "default_spot_limit": 11,
        "spot_ids": (
            "anderson_island_ferry",
            "yoman_point",
            "balch_passage",
            "eagle_island",
            "ketron_island",
            "steilacoom_ferry",
            "longbranch_marina",
            "devils_head",
            "pitt_passage",
            "drayton_passage",
            "nisqually_delta",
        ),
        "provider_context": ANDERSON_ISLAND_PROVIDER_CONTEXT,
    },
    "steilacoom_nisqually": {
        "id": "steilacoom_nisqually",
        "name": "Steilacoom & Nisqually",
        "type": "subregion",
        "center": {"lat": 47.1450, "lon": -122.6500},
        "default_zoom": 11,
        "default_spot_limit": 11,
        "spot_ids": (
            "steilacoom_ferry",
            "steilacoom_cormorant_passage",
            "sunnyside_beach",
            "chambers_creek_mouth",
            "ketron_island",
            "dupont_wharf",
            "nisqually_delta",
            "solo_point",
            "tolmie_state_park",
            "anderson_island_ferry",
            "balch_passage",
        ),
        "provider_context": STEILACOOM_PROVIDER_CONTEXT,
    },
    "olympia_budd_inlet": {
        "id": "olympia_budd_inlet",
        "name": "Olympia & Budd Inlet",
        "type": "city",
        "center": {"lat": 47.0983, "lon": -122.8950},
        "default_zoom": 11,
        "default_spot_limit": 11,
        "spot_ids": (
            "budd_inlet_entrance",
            "boston_harbor",
            "dofflemeyer_point",
            "swantown_marina",
            "olympia_port_plaza",
            "west_bay_park",
            "priest_point",
            "eld_inlet_entrance",
            "henderson_inlet",
            "tolmie_state_park",
            "nisqually_delta",
        ),
        "provider_context": OLYMPIA_BUDD_INLET_PROVIDER_CONTEXT,
    },
    "south_hood_canal": {
        "id": "south_hood_canal",
        "name": "South Hood Canal",
        "type": "subregion",
        "center": {"lat": 47.4183, "lon": -123.0200},
        "default_zoom": 10,
        "default_spot_limit": 12,
        "spot_ids": (
            "union_hood_canal",
            "lynch_cove",
            "belfair_state_park",
            "twanoh_state_park",
            "potlatch_state_park",
            "hama_hama",
            "lilliwaup",
            "ayock_point",
            "triton_head",
            "hazel_point",
            "seabeck_marina",
            "dosewallips_delta",
        ),
        "provider_context": SOUTH_HOOD_CANAL_PROVIDER_CONTEXT,
    },
    "aberdeen": {
        "id": "aberdeen",
        "name": "Aberdeen",
        "type": "city",
        "center": {"lat": 46.9754, "lon": -123.8157},
        "default_zoom": 11,
        "default_spot_limit": 12,
        "spot_ids": (
            "aberdeen_waterfront",
            "chehalis_river_mouth",
            "wishkah_river_mouth",
            "johns_river_mouth",
            "cosmopolis_chehalis",
            "bowerman_basin",
            "hoquiam_river_mouth",
            "grays_harbor_channel",
            "westport_marina",
            "half_moon_bay_westport",
            "grays_harbor_north_jetty",
            "grays_harbor_south_jetty",
        ),
        "provider_context": ABERDEEN_PROVIDER_CONTEXT,
    },
}

REGION_SEARCH_ALIASES = {
    DEFAULT_REGION_ID: (
        "Gig Harbor",
        "Purdy",
        "Purdy Bridge",
        "Henderson Bay",
        "Wollochet Bay",
        "Fox Island",
        "Hale Passage",
        "Kopachuck",
        "Narrows Park",
    ),
    "port_orchard": (
        "Port Orchard",
        "Annapolis",
        "Manchester",
        "Southworth",
        "Rich Passage",
        "Sinclair Inlet",
        "Waterman",
    ),
    "bremerton": (
        "Bremerton",
        "Manette",
        "Port Washington Narrows",
        "Warren Avenue Bridge",
        "Illahee",
        "Tracyton",
        "Oyster Bay",
        "Rocky Point",
    ),
    "silverdale": (
        "Silverdale",
        "Dyes Inlet",
        "Old Town Silverdale",
        "Clear Creek",
        "Barker Creek",
        "Brownsville",
    ),
    "tacoma_narrows": (
        "Tacoma Narrows",
        "Titlow",
        "Salmon Beach",
        "Day Island",
        "Point Defiance",
        "Point Ruston",
        "Chambers Creek",
    ),
    "carr_inlet": (
        "Carr Inlet",
        "Wauna",
        "Horsehead Bay",
        "Vaughn",
        "Home Spit",
        "Lakebay",
        "Penrose Point",
    ),
    "case_inlet": (
        "Case Inlet",
        "Allyn",
        "Grapeview",
        "Harstine",
        "Pickering Passage",
        "Squaxin Passage",
        "Jarrell Cove",
    ),
    "anderson_island": (
        "Anderson Island",
        "Ketron Island",
        "Balch Passage",
        "Eagle Island",
        "Longbranch",
        "Drayton Passage",
    ),
    "steilacoom_nisqually": (
        "Steilacoom",
        "Nisqually",
        "Nisqually Reach",
        "Cormorant Passage",
        "Sunnyside Beach",
        "DuPont",
        "Solo Point",
        "South Sound",
    ),
    "olympia_budd_inlet": (
        "Olympia",
        "Budd Inlet",
        "Boston Harbor",
        "Swantown",
        "West Bay",
        "Eld Inlet",
        "Henderson Inlet",
    ),
    "south_hood_canal": (
        "South Hood Canal",
        "Hood Canal",
        "Lynch Cove",
        "Twanoh",
        "Potlatch",
        "Hama Hama",
        "Lilliwaup",
        "Ayock Point",
        "Triton Head",
        "Hazel Point",
        "Seabeck",
        "Dosewallips",
    ),
    "aberdeen": (
        "Aberdeen",
        "Grays Harbor",
        "Hoquiam",
        "Cosmopolis",
        "Westport",
        "Half Moon Bay",
        "Bowerman Basin",
        "North Jetty",
        "South Jetty",
    ),
}

PLACE_REGION_ROUTES = {
    "belfair": {
        "term": "Belfair",
        "region_id": "south_hood_canal",
        "note": "Using South Hood Canal for Belfair.",
    },
    "union": {
        "term": "Union",
        "region_id": "south_hood_canal",
        "note": "Using South Hood Canal for Union.",
    },
    "chico": {
        "term": "Chico",
        "region_id": "silverdale",
        "note": "Using Silverdale for Chico.",
    },
    "gorst": {
        "term": "Gorst",
        "region_id": "bremerton",
        "note": "Using Bremerton for Gorst.",
    },
}


SHORELINE_EXPOSURE_BEARINGS = (
    ("grays harbor entrance", 250),
    ("north jetty", 245),
    ("south jetty", 260),
    ("westport", 245),
    ("south grays harbor", 215),
    ("north grays harbor", 205),
    ("grays harbor inner channel", 235),
    ("grays harbor channel", 245),
    ("chehalis river", 235),
    ("wishkah river", 230),
    ("hoquiam river", 230),
    ("hood canal west shore", 90),
    ("hood canal east shore", 270),
    ("south hood canal", 35),
    ("lynch cove", 220),
    ("union", 20),
    ("great bend", 20),
    ("hood canal", 35),
    ("tacoma narrows", 220),
    ("dalco passage", 45),
    ("day island", 210),
    ("south vashon", 200),
    ("commencement bay", 45),
    ("cormorant passage", 230),
    ("nisqually reach", 260),
    ("nisqually", 260),
    ("carr inlet", 180),
    ("case inlet", 180),
    ("rocky bay", 170),
    ("mayo cove", 190),
    ("pickering passage", 210),
    ("squaxin passage", 210),
    ("balch passage", 220),
    ("drayton passage", 210),
    ("pitt passage", 210),
    ("filucy bay", 190),
    ("budd inlet", 350),
    ("eld inlet", 220),
    ("henderson inlet", 210),
    ("sinclair inlet south shore", 0),
    ("sinclair inlet north shore", 180),
    ("sinclair inlet head", 70),
    ("sinclair inlet", 180),
    ("rich passage approach", 95),
    ("rich passage", 100),
    ("colvos passage approach", 110),
    ("colvos passage", 110),
    ("port washington narrows", 90),
    ("port orchard / dyes inlet approach", 120),
    ("port orchard / brownsville", 110),
    ("dyes inlet north shore", 180),
    ("dyes inlet east shore", 270),
    ("dyes inlet west shore", 90),
    ("dyes inlet / sinclair approach", 120),
    ("dyes inlet", 180),
    ("phinney bay", 140),
    ("oyster bay", 110),
    ("chico bay", 120),
    ("chico creek", 120),
    ("blackjack creek", 20),
    ("south kitsap", 210),
    ("clear creek", 180),
)


def _wind_exposure_bearing_for_shoreline(shoreline: str) -> int:
    """Returns the reviewed shoreline-family fetch bearing for regional spots."""
    normalized = shoreline.lower()
    for keyword, bearing in SHORELINE_EXPOSURE_BEARINGS:
        if keyword in normalized:
            return bearing
    return 225


def _regional_spot(
    title: str,
    ui_prefix: str,
    lat: float,
    lon: float,
    current_multiplier: float,
    wind_multiplier: float,
    active_by_default: bool = True,
    fixed_current: float | None = None,
    activity_tags: tuple[str, ...] = ("kayak", "fish"),
    access_note: str = "",
    shoreline: str = "",
    wind_exposure_bearing: int | None = None,
) -> dict:
    exposure_bearing = (
        wind_exposure_bearing
        if wind_exposure_bearing is not None
        else _wind_exposure_bearing_for_shoreline(shoreline)
    )
    spot = {
        "title": title,
        "ui_prefix": ui_prefix,
        "lat": lat,
        "lon": lon,
        "wind_multiplier": wind_multiplier,
        "wind_exposure_bearing": exposure_bearing,
        "wind_exposure_basis": "spot" if wind_exposure_bearing is not None else "shoreline_family",
        "kayak_rule_profile": "generic",
        "fish_rule_profile": "generic",
        "active_by_default": active_by_default,
        "activity_tags": activity_tags,
        "access_note": access_note,
        "shoreline": shoreline,
    }
    if fixed_current is not None:
        spot["fixed_current"] = fixed_current
    else:
        spot["current_multiplier"] = current_multiplier
    return spot


REVIEWED_SPOT_EXPOSURE_BEARINGS = {
    "port_orchard_waterfront": 45,
    "annapolis_foot_ferry": 20,
    "rich_passage_south_shore": 5,
    "bremerton_marina": 120,
    "manette_bridge": 90,
    "silverdale_waterfront_park": 185,
    "clear_creek_estuary": 180,
    "tacoma_narrows_bridge": 210,
    "titlow_beach": 250,
    "case_inlet_north": 175,
    "anderson_island_ferry": 95,
    "steilacoom_ferry": 280,
    "olympia_port_plaza": 350,
    "union_hood_canal": 190,
    "lynch_cove": 120,
    "aberdeen_waterfront": 240,
    "westport_marina": 270,
}


def _apply_reviewed_spot_exposure_bearings(spots: dict) -> dict:
    """Marks selected regional spots with reviewed fetch bearings."""
    for spot_id, bearing in REVIEWED_SPOT_EXPOSURE_BEARINGS.items():
        if spot_id not in spots:
            continue
        spots[spot_id]["wind_exposure_bearing"] = bearing
        spots[spot_id]["wind_exposure_basis"] = "spot_reviewed"
    return spots


REGIONAL_SPOTS = {
    "port_orchard_waterfront": _regional_spot(
        "PORT ORCHARD WATERFRONT",
        "powater",
        47.542,
        -122.638,
        0.55,
        0.85,
        access_note="Downtown shoreline and marina-adjacent public waterfront.",
        shoreline="Sinclair Inlet south shore",
    ),
    "port_orchard_marina": _regional_spot(
        "PORT ORCHARD MARINA",
        "pomarina",
        47.541,
        -122.637,
        0.45,
        0.75,
        access_note="Protected marina basin; treat traffic lanes conservatively.",
        shoreline="Sinclair Inlet",
    ),
    "annapolis_foot_ferry": _regional_spot(
        "ANNAPOLIS FOOT FERRY",
        "annapolis",
        47.548,
        -122.624,
        0.7,
        0.95,
        access_note="Pocket shoreline near the Port Orchard-Bremerton ferry route.",
        shoreline="Sinclair Inlet",
    ),
    "blackjack_creek_mouth": _regional_spot(
        "BLACKJACK CREEK MOUTH",
        "blackjack",
        47.536,
        -122.649,
        0.25,
        0.65,
        fixed_current=0.15,
        access_note="Estuary edge; shallow water and mudflat timing matter.",
        shoreline="Blackjack Creek estuary",
    ),
    "ross_point": _regional_spot(
        "ROSS POINT",
        "rosspoint",
        47.528,
        -122.671,
        0.8,
        1.05,
        access_note="Exposed bend between Gorst and Port Orchard.",
        shoreline="Sinclair Inlet south shore",
    ),
    "waterman_pier": _regional_spot(
        "WATERMAN PIER",
        "waterman",
        47.504,
        -122.546,
        0.65,
        1.1,
        access_note="South Kitsap shoreline with stronger south-wind exposure.",
        shoreline="Colvos Passage approach",
    ),
    "manchester_dock": _regional_spot(
        "MANCHESTER DOCK",
        "mancdock",
        47.555,
        -122.545,
        0.75,
        1.15,
        access_note="Open-water access near ferry traffic and Blake Island fetch.",
        shoreline="Rich Passage approach",
    ),
    "manchester_state_park": _regional_spot(
        "MANCHESTER STATE PARK",
        "mancpark",
        47.576,
        -122.550,
        0.6,
        1.05,
        access_note="Park shoreline with better beach room than downtown edges.",
        shoreline="Rich Passage",
    ),
    "southworth_ferry": _regional_spot(
        "SOUTHWORTH FERRY",
        "southworth",
        47.512,
        -122.500,
        0.8,
        1.2,
        access_note="Exposed ferry-terminal water; watch vessel wakes.",
        shoreline="Colvos Passage",
    ),
    "rich_passage_south_shore": _regional_spot(
        "RICH PASSAGE SOUTH SHORE",
        "richsouth",
        47.575,
        -122.563,
        0.9,
        1.2,
        access_note="Current-influenced shoreline between Manchester and Port Orchard.",
        shoreline="Rich Passage",
    ),
    "sinclair_inlet_south_shore": _regional_spot(
        "SINCLAIR INLET SOUTH SHORE",
        "sinsouth",
        47.535,
        -122.664,
        0.45,
        0.85,
        access_note="Sheltered inlet edge; shallow areas uncover on lower tides.",
        shoreline="Sinclair Inlet",
    ),
    "long_lake_estuary": _regional_spot(
        "LONG LAKE ESTUARY",
        "longlake",
        47.530,
        -122.603,
        0.2,
        0.65,
        fixed_current=0.1,
        active_by_default=False,
        access_note="Low-current backwater option; confirm local access before launching.",
        shoreline="South Kitsap estuary",
    ),
    "bremerton_marina": _regional_spot(
        "BREMERTON MARINA",
        "bremmarina",
        47.562,
        -122.625,
        0.45,
        0.8,
        access_note="Urban waterfront; stay clear of ferry and marina traffic.",
        shoreline="Sinclair Inlet north shore",
    ),
    "bremerton_ferry_terminal": _regional_spot(
        "BREMERTON FERRY TERMINAL",
        "bremferry",
        47.561,
        -122.624,
        0.65,
        1.0,
        access_note="High-traffic waterfront; useful as a conditions reference more than a launch.",
        shoreline="Sinclair Inlet",
    ),
    "evergreen_rotary_park": _regional_spot(
        "EVERGREEN ROTARY PARK",
        "evergreen",
        47.568,
        -122.631,
        0.35,
        0.75,
        access_note="Protected park shoreline near downtown Bremerton.",
        shoreline="Port Washington Narrows",
    ),
    "manette_bridge": _regional_spot(
        "MANETTE BRIDGE",
        "manette",
        47.570,
        -122.622,
        0.95,
        1.0,
        access_note="Narrow passage with stronger flow under and near the bridge.",
        shoreline="Port Washington Narrows",
    ),
    "lions_park_bremerton": _regional_spot(
        "LIONS PARK",
        "lions",
        47.583,
        -122.628,
        0.55,
        0.85,
        access_note="Park shoreline north of downtown with moderate narrows influence.",
        shoreline="Port Washington Narrows",
    ),
    "port_washington_narrows": _regional_spot(
        "PORT WASHINGTON NARROWS",
        "pwnarrows",
        47.578,
        -122.630,
        1.2,
        1.05,
        access_note="Current-focused planning point; best handled around slack.",
        shoreline="Port Washington Narrows",
    ),
    "warren_ave_bridge": _regional_spot(
        "WARREN AVE BRIDGE",
        "warren",
        47.580,
        -122.631,
        1.25,
        1.05,
        access_note="NOAA current context is nearby; expect compressed flow.",
        shoreline="Port Washington Narrows",
    ),
    "illahee_state_park": _regional_spot(
        "ILLAHEE STATE PARK",
        "illahee",
        47.598,
        -122.592,
        0.65,
        1.0,
        access_note="Park shoreline on the east side of the Dyes Inlet approach.",
        shoreline="Port Orchard / Dyes Inlet approach",
    ),
    "tracyton_beach": _regional_spot(
        "TRACYTON BEACH",
        "tracyton",
        47.608,
        -122.655,
        0.4,
        0.8,
        access_note="Sheltered Dyes Inlet shoreline near Tracyton.",
        shoreline="Dyes Inlet",
    ),
    "phinney_bay": _regional_spot(
        "PHINNEY BAY",
        "phinney",
        47.565,
        -122.661,
        0.25,
        0.65,
        fixed_current=0.12,
        access_note="Low-current bay option west of downtown Bremerton.",
        shoreline="Phinney Bay",
    ),
    "oyster_bay_bremerton": _regional_spot(
        "OYSTER BAY",
        "oyster",
        47.584,
        -122.692,
        0.2,
        0.6,
        fixed_current=0.1,
        access_note="Sheltered bay between Chico, Gorst, and Bremerton.",
        shoreline="Oyster Bay",
    ),
    "rocky_point_bremerton": _regional_spot(
        "ROCKY POINT",
        "rockypt",
        47.563,
        -122.682,
        0.35,
        0.75,
        access_note="West Bremerton shoreline with mixed fetch by wind direction.",
        shoreline="Dyes Inlet / Sinclair approach",
    ),
    "silverdale_waterfront_park": _regional_spot(
        "SILVERDALE WATERFRONT PARK",
        "silvpark",
        47.645,
        -122.696,
        0.2,
        0.6,
        fixed_current=0.08,
        access_note="Protected head-of-inlet shoreline; low tides expose flats.",
        shoreline="Dyes Inlet",
    ),
    "old_town_silverdale": _regional_spot(
        "OLD TOWN SILVERDALE",
        "oldtown",
        47.644,
        -122.694,
        0.2,
        0.6,
        fixed_current=0.08,
        access_note="Sheltered town shoreline near the upper inlet.",
        shoreline="Dyes Inlet",
    ),
    "clear_creek_estuary": _regional_spot(
        "CLEAR CREEK ESTUARY",
        "clearcreek",
        47.650,
        -122.696,
        0.15,
        0.55,
        fixed_current=0.06,
        access_note="Estuary/mudflat edge; tide height controls practical access.",
        shoreline="Clear Creek",
    ),
    "dyes_inlet_north_shore": _regional_spot(
        "DYES INLET NORTH SHORE",
        "dyesnorth",
        47.657,
        -122.692,
        0.25,
        0.7,
        access_note="North-shore Dyes Inlet reference point with broad shallow flats.",
        shoreline="Dyes Inlet",
    ),
    "barker_creek_mouth": _regional_spot(
        "BARKER CREEK MOUTH",
        "barker",
        47.642,
        -122.665,
        0.2,
        0.65,
        fixed_current=0.08,
        access_note="Shallow creek-mouth area; avoid disturbing sensitive flats.",
        shoreline="Dyes Inlet east shore",
    ),
    "dyes_inlet_east_shore": _regional_spot(
        "DYES INLET EAST SHORE",
        "dyeseast",
        47.630,
        -122.640,
        0.3,
        0.75,
        access_note="East-shore reference between Silverdale and Tracyton.",
        shoreline="Dyes Inlet",
    ),
    "brownsville_marina": _regional_spot(
        "BROWNSVILLE MARINA",
        "brownsville",
        47.649,
        -122.615,
        0.45,
        0.85,
        access_note="More open than inner Dyes Inlet; exposed to longer fetch.",
        shoreline="Port Orchard / Brownsville",
    ),
    "chico_bay_north": _regional_spot(
        "CHICO BAY",
        "chicobay",
        47.614,
        -122.714,
        0.18,
        0.55,
        fixed_current=0.08,
        access_note="Sheltered bay between Gorst and Silverdale.",
        shoreline="Chico Bay",
    ),
    "chico_creek_estuary": _regional_spot(
        "CHICO CREEK ESTUARY",
        "chicocreek",
        47.613,
        -122.718,
        0.12,
        0.5,
        fixed_current=0.05,
        access_note="Estuary edge; prioritize higher water and habitat sensitivity.",
        shoreline="Chico Creek",
    ),
    "dyes_inlet_west_shore": _regional_spot(
        "DYES INLET WEST SHORE",
        "dyeswest",
        47.620,
        -122.705,
        0.22,
        0.65,
        access_note="West-shore Dyes Inlet reference near Chico.",
        shoreline="Dyes Inlet",
    ),
    "erlands_point": _regional_spot(
        "ERLANDS POINT",
        "erlands",
        47.596,
        -122.711,
        0.28,
        0.75,
        access_note="Point shoreline between Chico Bay and Oyster Bay.",
        shoreline="Dyes Inlet west shore",
    ),
    "gorst_creek_delta": _regional_spot(
        "GORST CREEK DELTA",
        "gorstdelta",
        47.523,
        -122.705,
        0.18,
        0.6,
        fixed_current=0.08,
        access_note="Very shallow head-of-inlet water; tide height is decisive.",
        shoreline="Sinclair Inlet head",
    ),
    "sinclair_inlet_head": _regional_spot(
        "SINCLAIR INLET HEAD",
        "sinhead",
        47.525,
        -122.692,
        0.25,
        0.65,
        fixed_current=0.1,
        access_note="Sheltered inlet head near Gorst; broad flats at lower tides.",
        shoreline="Sinclair Inlet",
    ),
    "tacoma_narrows_bridge": _regional_spot(
        "TACOMA NARROWS BRIDGE",
        "narbridge",
        47.2717,
        -122.552,
        1.35,
        1.25,
        access_note="High-current Narrows reference point; plan around slack unless experienced.",
        shoreline="Tacoma Narrows",
    ),
    "titlow_beach": _regional_spot(
        "TITLOW BEACH",
        "titlow",
        47.252,
        -122.546,
        0.9,
        1.05,
        access_note="Public shoreline south of the bridge with Narrows influence.",
        shoreline="Tacoma Narrows",
    ),
    "salmon_beach": _regional_spot(
        "SALMON BEACH",
        "salmon",
        47.286,
        -122.560,
        1.1,
        1.15,
        access_note="Current-influenced west-shore Narrows reference.",
        shoreline="Tacoma Narrows",
    ),
    "day_island": _regional_spot(
        "DAY ISLAND",
        "dayisland",
        47.236,
        -122.552,
        0.65,
        0.85,
        access_note="More protected basin south of the Narrows.",
        shoreline="Day Island",
    ),
    "tahlequah_ferry": _regional_spot(
        "TAHLEQUAH FERRY",
        "tahlequah",
        47.333,
        -122.507,
        0.95,
        1.15,
        access_note="Ferry-route water with Dalco Passage influence.",
        shoreline="South Vashon",
    ),
    "point_defiance_owen_beach": _regional_spot(
        "OWEN BEACH",
        "owen",
        47.309,
        -122.527,
        0.75,
        1.05,
        access_note="Point Defiance shoreline; wakes and ferry traffic matter.",
        shoreline="Dalco Passage",
    ),
    "point_ruston": _regional_spot(
        "POINT RUSTON",
        "ruston",
        47.298,
        -122.510,
        0.45,
        0.8,
        access_note="Urban Commencement Bay shoreline with lighter current.",
        shoreline="Commencement Bay",
    ),
    "chambers_creek_mouth": _regional_spot(
        "CHAMBERS CREEK MOUTH",
        "chambers",
        47.200,
        -122.570,
        0.45,
        0.8,
        access_note="Creek-mouth shoreline; tide height changes the beach shape.",
        shoreline="Cormorant Passage",
    ),
    "wauna_waterfront": _regional_spot(
        "WAUNA WATERFRONT",
        "wauna",
        47.378,
        -122.634,
        0.85,
        0.85,
        access_note="Station-backed Carr Inlet reference near the Purdy reach.",
        shoreline="Carr Inlet",
    ),
    "vaughn_bay": _regional_spot(
        "VAUGHN BAY",
        "vaughn",
        47.342,
        -122.775,
        0.35,
        0.75,
        access_note="Protected bay with shallow edges and local access constraints.",
        shoreline="Case Inlet / Carr Inlet",
    ),
    "home_spit": _regional_spot(
        "HOME SPIT",
        "home",
        47.275,
        -122.758,
        0.45,
        0.85,
        access_note="Key Peninsula shoreline near Von Geldern Cove.",
        shoreline="Carr Inlet",
    ),
    "lakebay_marina": _regional_spot(
        "LAKEBAY MARINA",
        "lakebay",
        47.258,
        -122.757,
        0.35,
        0.75,
        access_note="Sheltered south Carr Inlet reference.",
        shoreline="Mayo Cove",
    ),
    "cutts_island": _regional_spot(
        "CUTTS ISLAND",
        "cutts",
        47.322,
        -122.694,
        0.45,
        0.95,
        access_note="Island shoreline with wake and wind exposure.",
        shoreline="Carr Inlet",
    ),
    "rocky_bay": _regional_spot(
        "ROCKY BAY",
        "rockybay",
        47.339,
        -122.789,
        0.3,
        0.7,
        access_note="Sheltered bay reference between Carr and Case Inlets.",
        shoreline="Rocky Bay",
    ),
    "penrose_point": _regional_spot(
        "PENROSE POINT",
        "penrose",
        47.260,
        -122.750,
        0.45,
        0.85,
        access_note="State park shoreline on the south Carr Inlet side.",
        shoreline="Carr Inlet",
    ),
    "allyn_waterfront": _regional_spot(
        "ALLYN WATERFRONT",
        "allyn",
        47.383,
        -122.823,
        0.3,
        0.65,
        access_note="Head-of-inlet shoreline; tide height controls practical water.",
        shoreline="Case Inlet",
    ),
    "case_inlet_north": _regional_spot(
        "CASE INLET NORTH",
        "casenorth",
        47.365,
        -122.840,
        0.45,
        0.85,
        access_note="North Case Inlet reference with longer southerly fetch.",
        shoreline="Case Inlet",
    ),
    "mcmicken_island": _regional_spot(
        "MCMICKEN ISLAND",
        "mcmicken",
        47.247,
        -122.862,
        0.55,
        1.0,
        access_note="Island/tombolo area; respect park and habitat rules.",
        shoreline="Case Inlet",
    ),
    "stretch_island": _regional_spot(
        "STRETCH ISLAND",
        "stretch",
        47.278,
        -122.835,
        0.5,
        0.95,
        access_note="South Case Inlet island shoreline.",
        shoreline="Case Inlet",
    ),
    "grapeview": _regional_spot(
        "GRAPEVIEW",
        "grapeview",
        47.329,
        -122.833,
        0.35,
        0.8,
        access_note="Case Inlet shoreline near Fair Harbor.",
        shoreline="Case Inlet",
    ),
    "jarrell_cove": _regional_spot(
        "JARRELL COVE",
        "jarrell",
        47.282,
        -122.884,
        0.25,
        0.65,
        access_note="Protected Harstine Island cove.",
        shoreline="Pickering Passage",
    ),
    "pickering_passage_north": _regional_spot(
        "PICKERING PASSAGE NORTH",
        "picknorth",
        47.306,
        -122.851,
        0.75,
        0.95,
        access_note="Current-influenced north Pickering Passage reference.",
        shoreline="Pickering Passage",
    ),
    "harstine_bridge": _regional_spot(
        "HARSTINE BRIDGE",
        "harstine",
        47.242,
        -122.888,
        0.65,
        0.9,
        access_note="Bridge passage with focused current.",
        shoreline="Pickering Passage",
    ),
    "squaxin_passage": _regional_spot(
        "SQUAXIN PASSAGE",
        "squaxin",
        47.176,
        -122.919,
        0.75,
        0.95,
        access_note="Current-influenced passage north of Hunter Point.",
        shoreline="Squaxin Passage",
    ),
    "anderson_island_ferry": _regional_spot(
        "ANDERSON ISLAND FERRY",
        "andyferry",
        47.173,
        -122.604,
        0.65,
        0.95,
        access_note="Ferry-route water; watch wakes and crossings.",
        shoreline="Cormorant Passage",
    ),
    "yoman_point": _regional_spot(
        "YOMAN POINT",
        "yoman",
        47.180,
        -122.675,
        0.75,
        0.9,
        access_note="Station-backed Anderson Island shoreline reference.",
        shoreline="Balch Passage",
    ),
    "balch_passage": _regional_spot(
        "BALCH PASSAGE",
        "balch",
        47.191,
        -122.692,
        0.95,
        1.0,
        access_note="Current-focused passage near Eagle Island.",
        shoreline="Balch Passage",
    ),
    "eagle_island": _regional_spot(
        "EAGLE ISLAND",
        "eagle",
        47.190,
        -122.700,
        0.75,
        0.95,
        access_note="Island shoreline with current and wind exposure.",
        shoreline="Balch Passage",
    ),
    "ketron_island": _regional_spot(
        "KETRON ISLAND",
        "ketron",
        47.150,
        -122.634,
        0.9,
        1.0,
        access_note="Open passage water; use conservative current windows.",
        shoreline="Cormorant Passage",
    ),
    "steilacoom_ferry": _regional_spot(
        "STEILACOOM FERRY",
        "steilferry",
        47.173,
        -122.603,
        0.65,
        0.9,
        access_note="Ferry terminal water with current and wake exposure.",
        shoreline="Cormorant Passage",
    ),
    "longbranch_marina": _regional_spot(
        "LONGBRANCH MARINA",
        "longbranch",
        47.210,
        -122.753,
        0.35,
        0.75,
        access_note="Protected Filucy Bay shoreline.",
        shoreline="Filucy Bay",
    ),
    "devils_head": _regional_spot(
        "DEVILS HEAD",
        "devils",
        47.161,
        -122.789,
        0.95,
        1.0,
        access_note="Current station nearby; exposed to Drayton Passage flow.",
        shoreline="Drayton Passage",
    ),
    "pitt_passage": _regional_spot(
        "PITT PASSAGE",
        "pitt",
        47.224,
        -122.711,
        0.75,
        0.85,
        access_note="Narrow passage near Pitt Island.",
        shoreline="Pitt Passage",
    ),
    "drayton_passage": _regional_spot(
        "DRAYTON PASSAGE",
        "drayton",
        47.173,
        -122.741,
        0.85,
        0.95,
        access_note="Current-influenced passage on the Key Peninsula side.",
        shoreline="Drayton Passage",
    ),
    "steilacoom_cormorant_passage": _regional_spot(
        "CORMORANT PASSAGE",
        "cormorant",
        47.173,
        -122.603,
        0.8,
        0.95,
        access_note="Steilacoom passage reference near the Anderson ferry route.",
        shoreline="Cormorant Passage",
    ),
    "sunnyside_beach": _regional_spot(
        "SUNNYSIDE BEACH",
        "sunnyside",
        47.167,
        -122.588,
        0.45,
        0.8,
        access_note="Public beach south of Steilacoom.",
        shoreline="Cormorant Passage",
    ),
    "dupont_wharf": _regional_spot(
        "DUPONT WHARF",
        "dupont",
        47.118,
        -122.665,
        0.5,
        0.85,
        access_note="Nisqually Reach shoreline with tide-flat influence.",
        shoreline="Nisqually Reach",
    ),
    "nisqually_delta": _regional_spot(
        "NISQUALLY DELTA",
        "nisqually",
        47.105,
        -122.700,
        0.35,
        0.7,
        access_note="Sensitive tide-flat habitat; use as conditions context.",
        shoreline="Nisqually Reach",
    ),
    "solo_point": _regional_spot(
        "SOLO POINT",
        "solo",
        47.124,
        -122.565,
        0.45,
        0.85,
        access_note="Open JBLM shoreline reference; access may be restricted.",
        shoreline="Nisqually Reach",
    ),
    "tolmie_state_park": _regional_spot(
        "TOLMIE STATE PARK",
        "tolmie",
        47.121,
        -122.772,
        0.3,
        0.7,
        access_note="Protected park shoreline on the east side of Olympia approaches.",
        shoreline="Nisqually / Henderson reach",
    ),
    "budd_inlet_entrance": _regional_spot(
        "BUDD INLET ENTRANCE",
        "buddentr",
        47.140,
        -122.921,
        0.85,
        0.95,
        access_note="Current station-backed entrance to Budd Inlet.",
        shoreline="Budd Inlet",
    ),
    "boston_harbor": _regional_spot(
        "BOSTON HARBOR",
        "boston",
        47.140,
        -122.903,
        0.45,
        0.8,
        access_note="Protected marina/harbor shoreline north of Olympia.",
        shoreline="Budd Inlet",
    ),
    "dofflemeyer_point": _regional_spot(
        "DOFFLEMEYER POINT",
        "doff",
        47.142,
        -122.903,
        0.55,
        0.85,
        access_note="Budd Inlet reference point near Boston Harbor.",
        shoreline="Budd Inlet",
    ),
    "swantown_marina": _regional_spot(
        "SWANTOWN MARINA",
        "swantown",
        47.057,
        -122.899,
        0.2,
        0.6,
        fixed_current=0.08,
        access_note="Protected inner Budd Inlet marina basin.",
        shoreline="Budd Inlet",
    ),
    "olympia_port_plaza": _regional_spot(
        "OLYMPIA PORT PLAZA",
        "olyport",
        47.049,
        -122.904,
        0.18,
        0.55,
        fixed_current=0.08,
        access_note="Inner Olympia water; tide height and harbor traffic matter.",
        shoreline="Budd Inlet",
    ),
    "west_bay_park": _regional_spot(
        "WEST BAY PARK",
        "westbay",
        47.056,
        -122.914,
        0.2,
        0.6,
        fixed_current=0.08,
        access_note="Sheltered west Budd Inlet shoreline.",
        shoreline="Budd Inlet",
    ),
    "priest_point": _regional_spot(
        "PRIEST POINT",
        "priest",
        47.071,
        -122.905,
        0.25,
        0.65,
        fixed_current=0.1,
        access_note="Forested park shoreline in lower Budd Inlet.",
        shoreline="Budd Inlet",
    ),
    "eld_inlet_entrance": _regional_spot(
        "ELD INLET ENTRANCE",
        "eld",
        47.146,
        -122.933,
        0.5,
        0.8,
        access_note="Subordinate current station nearby; use confidence labeling.",
        shoreline="Eld Inlet",
    ),
    "henderson_inlet": _regional_spot(
        "HENDERSON INLET",
        "henderson",
        47.155,
        -122.838,
        0.35,
        0.75,
        access_note="Shallow inlet shoreline; tide height matters.",
        shoreline="Henderson Inlet",
    ),
    "union_hood_canal": _regional_spot(
        "UNION",
        "union",
        47.358,
        -123.098,
        0.25,
        0.7,
        fixed_current=0.12,
        access_note="NOAA tide station-backed head-of-canal reference; shallow flats at lower water.",
        shoreline="Union / Great Bend",
    ),
    "lynch_cove": _regional_spot(
        "LYNCH COVE",
        "lynch",
        47.418,
        -122.900,
        0.18,
        0.6,
        fixed_current=0.08,
        access_note="Very shallow headwater cove; use higher tide windows and conservative current assumptions.",
        shoreline="Lynch Cove",
    ),
    "belfair_state_park": _regional_spot(
        "BELFAIR STATE PARK",
        "belfair",
        47.426,
        -122.872,
        0.2,
        0.65,
        fixed_current=0.08,
        access_note="Public park shoreline near the head of Hood Canal; tide flats dominate access.",
        shoreline="Lynch Cove",
    ),
    "twanoh_state_park": _regional_spot(
        "TWANOH STATE PARK",
        "twanoh",
        47.374,
        -123.007,
        0.3,
        0.75,
        access_note="South-shore park shoreline; watch afternoon thermal wind along the canal.",
        shoreline="South Hood Canal",
    ),
    "potlatch_state_park": _regional_spot(
        "POTLATCH STATE PARK",
        "potlatch",
        47.354,
        -123.162,
        0.35,
        0.85,
        access_note="Open canal shoreline with longer north-south fetch.",
        shoreline="South Hood Canal",
    ),
    "hama_hama": _regional_spot(
        "HAMA HAMA",
        "hamahama",
        47.557,
        -123.052,
        0.35,
        0.85,
        access_note="River-mouth and oyster-ground area; confirm legal access and shellfish closures.",
        shoreline="Hood Canal west shore",
    ),
    "lilliwaup": _regional_spot(
        "LILLIWAUP",
        "lilliwaup",
        47.463,
        -123.113,
        0.3,
        0.8,
        access_note="Small-cove shoreline with steep local terrain and variable wind.",
        shoreline="Hood Canal west shore",
    ),
    "ayock_point": _regional_spot(
        "AYOCK POINT",
        "ayock",
        47.508,
        -123.052,
        0.45,
        0.9,
        access_note="NOAA tide-station candidate shoreline; more exposed than inner Lynch Cove.",
        shoreline="Hood Canal",
    ),
    "triton_head": _regional_spot(
        "TRITON HEAD",
        "triton",
        47.603,
        -122.970,
        0.45,
        0.95,
        access_note="Broader-canal reference; wind fetch can build quickly.",
        shoreline="Hood Canal",
    ),
    "hazel_point": _regional_spot(
        "HAZEL POINT",
        "hazel",
        47.661,
        -122.872,
        0.75,
        0.95,
        access_note="Current station-backed Hood Canal reference, north of the South Hood core.",
        shoreline="Hood Canal",
    ),
    "seabeck_marina": _regional_spot(
        "SEABECK",
        "seabeck",
        47.638,
        -122.828,
        0.35,
        0.8,
        access_note="Central Hood Canal town shoreline; useful upper-bound context for South Hood trips.",
        shoreline="Hood Canal east shore",
    ),
    "dosewallips_delta": _regional_spot(
        "DOSEWALLIPS DELTA",
        "dosewallips",
        47.687,
        -122.905,
        0.25,
        0.75,
        fixed_current=0.1,
        active_by_default=False,
        access_note="Sensitive river-delta/tide-flat reference; check closures and habitat rules.",
        shoreline="Hood Canal west shore",
    ),
    "aberdeen_waterfront": _regional_spot(
        "ABERDEEN WATERFRONT",
        "abdwater",
        46.975,
        -123.815,
        0.45,
        0.75,
        access_note="Chehalis River waterfront; tide predictions are useful but river flow can dominate.",
        shoreline="Chehalis River",
    ),
    "chehalis_river_mouth": _regional_spot(
        "CHEHALIS RIVER MOUTH",
        "chehalis",
        46.970,
        -123.855,
        0.65,
        0.9,
        access_note="River-to-harbor transition; treat ebb against ocean swell conservatively.",
        shoreline="Grays Harbor inner channel",
    ),
    "wishkah_river_mouth": _regional_spot(
        "WISHKAH RIVER MOUTH",
        "wishkah",
        46.974,
        -123.814,
        0.35,
        0.65,
        fixed_current=0.15,
        access_note="Urban tributary mouth; freshwater runoff can distort tide/current timing.",
        shoreline="Wishkah River",
    ),
    "johns_river_mouth": _regional_spot(
        "JOHNS RIVER MOUTH",
        "johnsriver",
        46.920,
        -123.955,
        0.45,
        0.85,
        access_note="South-bay river-mouth area; broad flats and weather exposure matter.",
        shoreline="South Grays Harbor",
    ),
    "cosmopolis_chehalis": _regional_spot(
        "COSMOPOLIS",
        "cosmo",
        46.955,
        -123.770,
        0.35,
        0.65,
        fixed_current=0.15,
        access_note="Upper Chehalis tidal reach; river stage can override marine guidance.",
        shoreline="Chehalis River",
    ),
    "bowerman_basin": _regional_spot(
        "BOWERMAN BASIN",
        "bowerman",
        46.974,
        -123.938,
        0.3,
        0.7,
        fixed_current=0.12,
        access_note="Tide-flat and wildlife refuge area; use as a conditions reference, not a launch recommendation.",
        shoreline="North Grays Harbor",
    ),
    "hoquiam_river_mouth": _regional_spot(
        "HOQUIAM RIVER MOUTH",
        "hoquiam",
        46.978,
        -123.890,
        0.45,
        0.75,
        access_note="River mouth near the navigation channel; current timing can be river-influenced.",
        shoreline="Hoquiam River / Grays Harbor",
    ),
    "grays_harbor_channel": _regional_spot(
        "GRAYS HARBOR CHANNEL",
        "ghchannel",
        46.935,
        -124.020,
        0.85,
        1.0,
        access_note="Main-channel reference; bar and vessel traffic risks are outside simple score thresholds.",
        shoreline="Grays Harbor",
    ),
    "westport_marina": _regional_spot(
        "WESTPORT MARINA",
        "westport",
        46.903,
        -124.105,
        0.55,
        0.9,
        access_note="Protected marina basin near ocean-facing water; use bar forecast for outside trips.",
        shoreline="Westport / Grays Harbor",
    ),
    "half_moon_bay_westport": _regional_spot(
        "HALF MOON BAY",
        "halfmoon",
        46.913,
        -124.110,
        0.5,
        0.95,
        access_note="Near-harbor shoreline exposed to coastal wind and swell wrap.",
        shoreline="Westport",
    ),
    "grays_harbor_north_jetty": _regional_spot(
        "NORTH JETTY",
        "ghnorthjetty",
        46.955,
        -124.150,
        0.95,
        1.25,
        access_note="Ocean-bar-adjacent reference; do not treat app scoring as bar-crossing guidance.",
        shoreline="Grays Harbor entrance",
    ),
    "grays_harbor_south_jetty": _regional_spot(
        "SOUTH JETTY",
        "ghsouthjetty",
        46.895,
        -124.130,
        0.95,
        1.25,
        access_note="Ocean-bar-adjacent reference; use official bar and coastal forecasts before going.",
        shoreline="Grays Harbor entrance",
    ),
}
REGIONAL_SPOTS = _apply_reviewed_spot_exposure_bearings(REGIONAL_SPOTS)


def _build_spots() -> dict:
    spots = {}
    for index, (spot_id, spot_config) in enumerate(ALL_ZONES.items(), start=1):
        spots[spot_id] = {
            "id": spot_id,
            **deepcopy(spot_config),
            "region_ids": (DEFAULT_REGION_ID,),
            "active_by_default": spot_id in ZONES,
            "priority": index,
        }
    for spot_id, spot_config in REGIONAL_SPOTS.items():
        spots[spot_id] = {
            "id": spot_id,
            **deepcopy(spot_config),
        }
    return spots


SPOTS = _build_spots()


def get_region(region_id: str = DEFAULT_REGION_ID) -> dict:
    """Returns a copy of a configured region."""
    try:
        region = deepcopy(REGIONS[region_id])
        region["default_spot_limit"] = len(region["spot_ids"])
        region["provider_context"] = describe_provider_context(region["provider_context"])
        return region
    except KeyError as exc:
        raise ValueError(f"Unknown TideWindow region: {region_id}") from exc


def ranked_spots_for_region(region_id: str = DEFAULT_REGION_ID) -> list[dict]:
    """Returns all spots for a region in deterministic relevance order."""
    region = get_region(region_id)
    spots = []
    for index, spot_id in enumerate(region["spot_ids"], start=1):
        spot = deepcopy(SPOTS[spot_id])
        spot["region_ids"] = tuple(sorted(set(spot.get("region_ids", ())) | {region_id}))
        spot["priority"] = spot.get("priority", index)
        default_active = spot.get("active_by_default", True)
        if region_id != DEFAULT_REGION_ID:
            default_active = default_active and index <= len(region["spot_ids"])
        spot["active_by_default"] = default_active
        spots.append(spot)
    return sorted(spots, key=lambda spot: spot.get("priority", 9999))


def visible_spots_for_region(region_id: str = DEFAULT_REGION_ID, limit: int | None = None) -> list[dict]:
    """Returns the visible ranked spots for a region.

    ``limit`` supports the "show fewer / show more" control. If omitted,
    all ranked spots for the selected region are visible.
    """
    region = get_region(region_id)
    max_spots = len(region["spot_ids"])
    spot_limit = max_spots if limit is None else max(0, int(limit))
    spot_limit = min(spot_limit, max_spots)
    return ranked_spots_for_region(region_id)[:spot_limit]


def region_summaries() -> list[dict]:
    """Returns public metadata for region/place selection controls."""
    summaries = []
    for region_id in REGIONS:
        region = get_region(region_id)
        summaries.append(
            {
                "id": region["id"],
                "name": region["name"],
                "type": region["type"],
                "center": region["center"],
                "default_zoom": region["default_zoom"],
                "default_spot_limit": region["default_spot_limit"],
                "spot_count": len(region["spot_ids"]),
            }
        )
    return summaries


def normalize_region_query(query: str) -> str:
    """Normalizes a user-entered place name for exact alias matching."""
    return re.sub(r"[^a-z0-9]+", " ", str(query).lower()).strip()


def region_search_aliases() -> list[dict]:
    """Returns searchable region, city, launch, and marine-area aliases."""
    entries_by_key = {}
    for region_id, aliases in REGION_SEARCH_ALIASES.items():
        region = get_region(region_id)
        terms = {
            region["id"].replace("_", " "),
            region["name"],
            *aliases,
        }
        for term in terms:
            normalized = normalize_region_query(term)
            if not normalized:
                continue
            entries_by_key.setdefault(
                normalized,
                {
                    "term": term,
                    "normalized": normalized,
                    "region_id": region["id"],
                    "region_name": region["name"],
                    "match_type": "region" if normalized in {
                        normalize_region_query(region["id"].replace("_", " ")),
                        normalize_region_query(region["name"]),
                    } else "alias",
                    "note": "",
                },
            )

    for route in PLACE_REGION_ROUTES.values():
        region = get_region(route["region_id"])
        term = route["term"]
        normalized = normalize_region_query(term)
        entries_by_key[normalized] = {
            "term": term,
            "normalized": normalized,
            "region_id": region["id"],
            "region_name": region["name"],
            "match_type": "nearby",
            "note": route["note"],
        }

    return sorted(
        entries_by_key.values(),
        key=lambda item: (item["term"].lower(), item["region_name"].lower()),
    )


def resolve_region_query(query: str) -> dict | None:
    """Resolves an exact normalized place query to a supported region alias."""
    normalized = normalize_region_query(query)
    if not normalized:
        return None
    for entry in region_search_aliases():
        if entry["normalized"] == normalized:
            return entry
    return None


def provider_context_for_region(region_id: str = DEFAULT_REGION_ID) -> dict:
    """Returns the station/weather provider context for a region."""
    return get_region(region_id)["provider_context"]


def zone_configs_for_region(region_id: str = DEFAULT_REGION_ID, limit: int | None = None) -> dict:
    """Returns region spots in the existing zone-config shape.

    This intentionally strips region-only metadata so existing scoring and API
    behavior remain compatible while the regional model is introduced.
    """
    spots = ranked_spots_for_region(region_id) if limit is None else visible_spots_for_region(region_id, limit)
    return {
        spot["id"]: {
            key: value
            for key, value in spot.items()
            if key not in {"id", "region_ids", "active_by_default", "priority"}
        }
        for spot in spots
    }


def default_spot_ids_for_region(region_id: str = DEFAULT_REGION_ID) -> tuple[str, ...]:
    """Returns the spot ids active by default for a region."""
    return tuple(
        spot["id"]
        for spot in ranked_spots_for_region(region_id)
        if spot.get("active_by_default")
    )


def optional_spot_ids_for_region(region_id: str = DEFAULT_REGION_ID) -> tuple[str, ...]:
    """Returns the spot ids available but not active by default."""
    return tuple(
        spot["id"]
        for spot in ranked_spots_for_region(region_id)
        if not spot.get("active_by_default")
    )


def region_count() -> int:
    """Returns the number of configured selectable regions."""
    return len(REGIONS)


def gig_harbor_parity_snapshot() -> dict:
    """Summarizes the current compatibility contract for tests."""
    return {
        "region_id": DEFAULT_REGION_ID,
        "zone_ids": tuple(zone_configs_for_region(DEFAULT_REGION_ID).keys()),
        "default_ids": default_spot_ids_for_region(DEFAULT_REGION_ID),
        "optional_ids": optional_spot_ids_for_region(DEFAULT_REGION_ID),
        "legacy_zone_ids": tuple(ALL_ZONES.keys()),
        "legacy_default_ids": tuple(ZONES.keys()),
        "legacy_optional_ids": tuple(OPTIONAL_ZONES.keys()),
    }
