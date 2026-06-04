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
    spots = [deepcopy(SPOTS[spot_id]) for spot_id in region["spot_ids"]]
    return sorted(spots, key=lambda spot: spot.get("priority", 9999))


def visible_spots_for_region(region_id: str = DEFAULT_REGION_ID, limit: int | None = None) -> list[dict]:
    """Returns the visible ranked spots for a region.

    ``limit`` supports the future "show fewer / show more" control. If omitted,
    it uses the region's default spot limit.
    """
    region = get_region(region_id)
    spot_limit = region["default_spot_limit"] if limit is None else max(0, int(limit))
    return ranked_spots_for_region(region_id)[:spot_limit]


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
