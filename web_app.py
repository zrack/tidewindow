import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from marine_config import (
    ALL_ZONES,
    DEFAULT_RISK_TOLERANCE,
    FORECAST_HOURS,
    NOAA_CURRENT_STATION,
    NOAA_TIDE_STATION,
    OPTIONAL_ZONES,
    RISK_TOLERANCE_PROFILES,
    WEATHER_LAT,
    WEATHER_LON,
    WEB_APP_NAME,
    WEB_REFRESH_INTERVAL_SECONDS,
    ZONES,
)
from marine_cache import MarineStateCache
from marine_engine import MarineSafetyEngine
from marine_regions import (
    DEFAULT_REGION_ID,
    get_region,
    default_spot_ids_for_region,
    provider_context_for_region,
    region_count,
    region_search_aliases,
    region_summaries,
    zone_configs_for_region,
)
from noaa_client import NoaaMarineClient
from sun_times import sun_events


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
APP_VERSION = "0.4.5"

app = FastAPI(title=WEB_APP_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Cache upstream marine state so reloads and multiple tabs don't each hit
# NOAA/OpenWeather, and so a brief upstream outage serves the last good
# reading instead of static seed data. Resolves NoaaMarineClient lazily so
# tests can patch it.
state_cache = MarineStateCache(
    WEB_REFRESH_INTERVAL_SECONDS,
    lambda: NoaaMarineClient(provider_context_for_region(DEFAULT_REGION_ID)),
)
region_state_caches = {}


def get_state_cache(region_id: str) -> MarineStateCache:
    """Returns a region-scoped upstream cache for the selected provider context."""
    if region_id == DEFAULT_REGION_ID:
        return state_cache
    if region_id not in region_state_caches:
        provider_context = provider_context_for_region(region_id)
        region_state_caches[region_id] = MarineStateCache(
            WEB_REFRESH_INTERVAL_SECONDS,
            lambda provider_context=provider_context: NoaaMarineClient(provider_context),
        )
    return region_state_caches[region_id]


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/service-worker.js")
async def service_worker():
    # Served from the root so its scope covers the whole app, not just /static.
    return FileResponse(
        STATIC_DIR / "service-worker.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": WEB_APP_NAME,
        "version": APP_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "zones": len(ALL_ZONES),
        "default_zones": len(ZONES),
        "optional_zones": len(OPTIONAL_ZONES),
        "regions": region_count(),
        "forecast_hours": FORECAST_HOURS,
        "refresh_seconds": WEB_REFRESH_INTERVAL_SECONDS,
        "providers": {
            "noaa_tide_station": NOAA_TIDE_STATION,
            "noaa_current_station": NOAA_CURRENT_STATION,
            "regions": [
                {
                    "id": region["id"],
                    "tide_station": provider_context_for_region(region["id"])["tide_station"],
                    "tide_station_type": provider_context_for_region(region["id"])["tide_station_type"],
                    "current_station": provider_context_for_region(region["id"])["current_station"],
                    "current_station_type": provider_context_for_region(region["id"])["current_station_type"],
                    "current_bin": provider_context_for_region(region["id"]).get("current_bin"),
                    "current_bin_depth_ft": provider_context_for_region(region["id"]).get("current_bin_depth_ft"),
                    "nws_zone": provider_context_for_region(region["id"])["nws_zone"],
                    "provider_confidence": provider_context_for_region(region["id"])["provider_confidence"]["level"],
                    "provider_confidence_label": provider_context_for_region(region["id"])["provider_confidence"].get("label"),
                    "provider_profile": provider_context_for_region(region["id"])["provider_strategy"]["profile"],
                    "provider_warnings": provider_context_for_region(region["id"])["provider_strategy"].get("warnings", ()),
                }
                for region in region_summaries()
            ],
            "openweather": "configured" if os.getenv("OPENWEATHER_API_KEY") else "optional_missing",
        },
    }


@app.get("/api/regions")
async def api_regions():
    return {
        "default_region": DEFAULT_REGION_ID,
        "regions": region_summaries(),
        "search_aliases": region_search_aliases(),
    }


@app.get("/api/state")
async def api_state(
    region: str = DEFAULT_REGION_ID,
    limit: int | None = None,
    risk: str = DEFAULT_RISK_TOLERANCE,
):
    engine = MarineSafetyEngine(risk)
    try:
        telemetry, forecast, cache_meta = await get_state_cache(region).get()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = build_state_payload(engine, telemetry, forecast, region_id=region, limit=limit)
    payload["cache"] = cache_meta
    return payload


def build_state_payload(
    engine,
    telemetry: dict,
    forecast: dict,
    region_id: str = DEFAULT_REGION_ID,
    limit: int | None = None,
) -> dict:
    """Assembles the dashboard payload from telemetry and forecast data."""
    try:
        region = get_region(region_id)
        zone_configs = zone_configs_for_region(region_id, limit=limit)
        default_spot_ids = set(default_spot_ids_for_region(region_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    zones = engine.get_zone_telemetry(
        telemetry["current_knots"],
        telemetry["tide_feet"],
        telemetry["wind_knots"],
        telemetry.get("wind_direction"),
        zones_config=zone_configs,
    )
    zone_cards = []
    for zone_id, zone_config in zone_configs.items():
        zone_data = zones[zone_id]
        kayak = engine.evaluate_kayaking(
            zone_id,
            zone_data["current"],
            zone_data["wind"],
            risk_tolerance=engine.risk_tolerance,
        )
        fish = engine.evaluate_fly_fishing(
            zone_id,
            zone_data["current"],
            zone_data["tide"],
            risk_tolerance=engine.risk_tolerance,
        )
        zone_cards.append(
            {
                "id": zone_id,
                "title": zone_config["title"],
                "active_by_default": zone_id in default_spot_ids,
                "map": {
                    "lat": zone_config.get("lat"),
                    "lon": zone_config.get("lon"),
                },
                "current": round(zone_data["current"], 2),
                "wind": round(zone_data["wind"], 1),
                "wind_direction": zone_data.get("wind_direction"),
                "wind_exposure": zone_data.get("wind_exposure"),
                "tide": round(zone_data["tide"], 1),
                "kayak": kayak,
                "fish": fish,
            }
        )

    windows = engine.build_forecast_windows(
        forecast.get("predictions", []),
        telemetry["wind_knots"],
        telemetry.get("wind_direction"),
        wind_predictions=forecast.get("wind_predictions", []),
        current_predictions=forecast.get("current_predictions", []),
        current_source=forecast.get("sources", {}).get("current", "derived"),
        wind_source=forecast.get("sources", {}).get("wind", "fallback"),
        zones_config=zone_configs,
    )
    timeline = engine.build_hourly_timeline(
        forecast.get("predictions", []),
        telemetry["wind_knots"],
        telemetry.get("wind_direction"),
        wind_predictions=forecast.get("wind_predictions", []),
        current_predictions=forecast.get("current_predictions", []),
        current_source=forecast.get("sources", {}).get("current", "derived"),
        wind_source=forecast.get("sources", {}).get("wind", "fallback"),
        zones_config=zone_configs,
    )
    confidence = engine.evaluate_confidence(
        telemetry,
        forecast,
        telemetry["wind_knots"],
    )
    digest = build_daily_digest(
        timeline,
        zone_configs,
        risk_tolerance=engine.risk_tolerance,
    )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": {
            "app": WEB_APP_NAME,
            "refresh_seconds": WEB_REFRESH_INTERVAL_SECONDS,
            "forecast_hours": FORECAST_HOURS,
            "risk_tolerance": {
                "id": engine.risk_tolerance,
                **RISK_TOLERANCE_PROFILES[engine.risk_tolerance],
                "options": [
                    {"id": key, **value}
                    for key, value in RISK_TOLERANCE_PROFILES.items()
                ],
            },
            "region": {
                "id": region["id"],
                "name": region["name"],
                "type": region["type"],
                "center": region["center"],
                "default_zoom": region["default_zoom"],
                "default_spot_limit": region["default_spot_limit"],
                "spot_count": len(region["spot_ids"]),
                "visible_spot_limit": len(zone_configs),
                "provider_context": region["provider_context"],
            },
        },
        "telemetry": telemetry,
        "forecast": {
            **forecast,
            "predictions": _serialize_points(forecast.get("predictions", [])),
            "wind_predictions": _serialize_points(forecast.get("wind_predictions", [])),
            "current_predictions": _serialize_points(forecast.get("current_predictions", [])),
            "tide_events": _serialize_points(forecast.get("tide_events", [])),
            "slack_events": _serialize_points(forecast.get("slack_events", [])),
        },
        "zones": zone_cards,
        "digest": _serialize_digest(digest),
        "windows": [_serialize_window(window) for window in windows],
        "timeline": [_serialize_window(window) for window in timeline],
        "confidence": confidence,
        "daylight": build_daylight(
            lat=region["provider_context"].get("weather_lat"),
            lon=region["provider_context"].get("weather_lon"),
        ),
        "alerts": forecast.get("alerts", []),
    }


def build_daily_digest(timeline: list, zones_config: dict, risk_tolerance: str) -> dict:
    """Builds a compact tomorrow recommendation digest from scored timeline hours."""
    target_date = (datetime.now() + timedelta(days=1)).date()
    tomorrow_items = [
        item for item in timeline
        if item["start"].date() == target_date
    ]
    picks = [
        _best_digest_item(tomorrow_items, zones_config, "Kayak", risk_tolerance),
        _best_digest_item(tomorrow_items, zones_config, "Fish", risk_tolerance),
    ]
    picks = [item for item in picks if item]

    return {
        "tomorrow": {
            "date": target_date.isoformat(),
            "label": "Tomorrow",
            "summary": _digest_summary(picks),
            "items": picks,
        }
    }


def _best_digest_item(timeline: list, zones_config: dict, activity: str, risk_tolerance: str) -> dict | None:
    key = "fish" if activity == "Fish" else "kayak"
    score_key = f"{key}_score"
    best = None

    for hour in timeline:
        for zone_id, zone in hour.get("zones", {}).items():
            score = zone.get(score_key, 0)
            if best and score <= best["score"]:
                continue
            evaluation = zone.get(key, {})
            zone_title = zones_config.get(zone_id, {}).get("title", zone_id)
            best = {
                "activity": activity,
                "zone_id": zone_id,
                "zone_title": zone_title,
                "start": hour["start"],
                "end": hour["end"],
                "status": evaluation.get("status", "UNKNOWN"),
                "color": evaluation.get("color", "yellow"),
                "score": score,
                "phase": hour["phase"],
                "current": zone["current"],
                "current_source": hour["current_source"],
                "wind": zone["wind"],
                "wind_source": hour["wind_source"],
                "tide": zone["tide"],
                "note": evaluation.get("note", ""),
                "why": _digest_why(activity, zone_title, evaluation, zone, hour, risk_tolerance),
            }

    return best


def _digest_summary(picks: list[dict]) -> str:
    if not picks:
        return "No scored tomorrow windows are available yet."
    return "Best tomorrow picks for kayaking and fishing in the selected region."


def _digest_why(
    activity: str,
    zone_title: str,
    evaluation: dict,
    zone: dict,
    hour: dict,
    risk_tolerance: str,
) -> str:
    status = str(evaluation.get("status", "scored")).title()
    return (
        f"{status} {activity.lower()} read at {zone_title}: "
        f"{zone['current']:.1f} kt current, {zone['wind']:.0f} kt wind, "
        f"{zone['tide']:.1f} ft tide, {hour['phase'].lower()}. "
        f"Uses {risk_tolerance} risk thresholds."
    )


def build_daylight(
    hours: int = FORECAST_HOURS,
    lat: str | float | None = WEATHER_LAT,
    lon: str | float | None = WEATHER_LON,
) -> dict:
    """Returns sunrise/sunset (and civil dawn/dusk) for each date in the window.

    Keyed by ISO date string so the frontend can shade each timeline hour.
    Computed locally from the configured coordinates, so it works without any
    weather API key.
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return {}

    now = datetime.now()
    end = now + timedelta(hours=hours)
    daylight = {}
    day = now.date()
    while day <= end.date():
        events = sun_events(lat, lon, day)
        daylight[day.isoformat()] = {
            key: (value.isoformat(timespec="minutes") if value else None)
            for key, value in events.items()
        }
        day = day + timedelta(days=1)
    return daylight


def _serialize_points(points: list) -> list:
    serialized = []
    for point in points:
        serialized.append(
            {
                key: value.isoformat(timespec="minutes") if hasattr(value, "isoformat") else value
                for key, value in point.items()
            }
        )
    return serialized


def _serialize_window(window: dict) -> dict:
    return {
        **window,
        "start": window["start"].isoformat(timespec="minutes"),
        "end": window["end"].isoformat(timespec="minutes"),
    }


def _serialize_digest(digest: dict) -> dict:
    tomorrow = digest.get("tomorrow", {})
    return {
        **digest,
        "tomorrow": {
            **tomorrow,
            "items": [_serialize_window(item) for item in tomorrow.get("items", [])],
        },
    }
