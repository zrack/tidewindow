"""Region and spot selection helpers for TideWindow.

This module is the first step toward city/place based selection. It keeps the
current Gig Harbor dashboard behavior intact while introducing data structures
that can later support places such as Port Orchard or Aberdeen.
"""

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

BREMERTON_TIDE_STATION = "9445958"
BREMERTON_PROVIDER_CONTEXT = {
    "tide_station": BREMERTON_TIDE_STATION,
    "current_station": "PUG1510",
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.5650",
    "weather_lon": "-122.6269",
}
PORT_ORCHARD_PROVIDER_CONTEXT = {
    "tide_station": BREMERTON_TIDE_STATION,
    "current_station": "PUG1514",
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.5404",
    "weather_lon": "-122.6362",
}
SILVERDALE_PROVIDER_CONTEXT = {
    "tide_station": BREMERTON_TIDE_STATION,
    "current_station": "PUG1510",
    "nws_zone": NWS_MARINE_ZONE,
    "weather_lat": "47.6445",
    "weather_lon": "-122.6949",
}

REGIONS = {
    DEFAULT_REGION_ID: {
        "id": DEFAULT_REGION_ID,
        "name": "Gig Harbor",
        "type": "city",
        "center": {"lat": 47.32, "lon": -122.61},
        "default_zoom": 11,
        "default_spot_limit": 10,
        "spot_ids": tuple(ALL_ZONES.keys()),
        "provider_context": {
            "tide_station": NOAA_TIDE_STATION,
            "current_station": NOAA_CURRENT_STATION,
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
        "default_spot_limit": 10,
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
        "default_spot_limit": 10,
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
        "default_spot_limit": 10,
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
}


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
) -> dict:
    spot = {
        "title": title,
        "ui_prefix": ui_prefix,
        "lat": lat,
        "lon": lon,
        "wind_multiplier": wind_multiplier,
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
}


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
        return deepcopy(REGIONS[region_id])
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
            default_active = default_active and index <= region["default_spot_limit"]
        spot["active_by_default"] = default_active
        spots.append(spot)
    return sorted(spots, key=lambda spot: spot.get("priority", 9999))


def visible_spots_for_region(region_id: str = DEFAULT_REGION_ID, limit: int | None = None) -> list[dict]:
    """Returns the visible ranked spots for a region.

    ``limit`` supports the future "show fewer / show more" control. If omitted,
    it uses the region's default spot limit.
    """
    region = get_region(region_id)
    max_spots = len(region["spot_ids"])
    spot_limit = region["default_spot_limit"] if limit is None else max(0, int(limit))
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
