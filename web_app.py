import hmac
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from digest_delivery import (
    DEFAULT_CLIENT_ID,
    DEFAULT_DELIVERY_TIME,
    DigestEmailSender,
    DigestPreferences,
    DigestPreferenceStore,
    DigestScheduler,
    build_digest_params,
    smtp_configured,
    validate_preferences,
    verify_unsubscribe_token,
)
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
from sun_times import sun_events


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
APP_VERSION = "0.5.0"

app = FastAPI(title=WEB_APP_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
digest_preference_store = DigestPreferenceStore()
digest_email_sender = DigestEmailSender()

# Cache upstream marine state so reloads and multiple tabs don't each hit
# NOAA/OpenWeather, and so a brief upstream outage serves the last good
# reading instead of static seed data. The NOAA client is resolved lazily so
# admin and scheduler imports do not pay the heavier provider startup cost.
state_cache = MarineStateCache(
    WEB_REFRESH_INTERVAL_SECONDS,
    lambda: create_noaa_client(provider_context_for_region(DEFAULT_REGION_ID)),
)
region_state_caches = {}


class DigestPreferenceRequest(BaseModel):
    enabled: bool = False
    email: str = ""
    delivery_time: str = DEFAULT_DELIVERY_TIME
    region: str = DEFAULT_REGION_ID
    activity: str = "All"
    risk: str = DEFAULT_RISK_TOLERANCE
    density: str = "full"


class DigestAdminPreferenceRequest(BaseModel):
    enabled: bool


def get_state_cache(region_id: str) -> MarineStateCache:
    """Returns a region-scoped upstream cache for the selected provider context."""
    if region_id == DEFAULT_REGION_ID:
        return state_cache
    if region_id not in region_state_caches:
        provider_context = provider_context_for_region(region_id)
        region_state_caches[region_id] = MarineStateCache(
            WEB_REFRESH_INTERVAL_SECONDS,
            lambda provider_context=provider_context: create_noaa_client(provider_context),
        )
    return region_state_caches[region_id]


def create_noaa_client(provider_context: dict):
    from noaa_client import NoaaMarineClient

    return NoaaMarineClient(provider_context)


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/digest")
async def digest_page():
    return FileResponse(STATIC_DIR / "digest.html")


@app.get("/unsubscribe")
async def unsubscribe_page():
    return FileResponse(STATIC_DIR / "unsubscribe.html")


@app.get("/admin")
async def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


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


@app.get("/api/digest")
async def api_digest(
    region: str = DEFAULT_REGION_ID,
    limit: int | None = None,
    risk: str = DEFAULT_RISK_TOLERANCE,
    activity: str = "All",
):
    payload = await api_state(region=region, limit=limit, risk=risk)
    digest = filter_digest_activity(payload["digest"], activity)
    response = {
        "generated_at": payload["generated_at"],
        "activity": normalize_digest_activity(activity),
        "config": {
            "app": payload["config"]["app"],
            "region": payload["config"]["region"],
            "risk_tolerance": payload["config"]["risk_tolerance"],
        },
        "digest": digest,
        "confidence": payload["confidence"],
        "cache": payload["cache"],
    }
    response["text"] = build_digest_text(response)
    return response


@app.get("/api/digest.ics")
async def api_digest_ics(
    region: str = DEFAULT_REGION_ID,
    limit: int | None = None,
    risk: str = DEFAULT_RISK_TOLERANCE,
    activity: str = "All",
):
    payload = await api_digest(region=region, limit=limit, risk=risk, activity=activity)
    content = build_digest_ics(payload)
    return Response(
        content=content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="tidewindow-digest.ics"'},
    )


@app.get("/api/digest-preferences")
async def api_digest_preferences(client_id: str = DEFAULT_CLIENT_ID):
    preferences = digest_preference_store.get(client_id)
    return digest_preferences_response(client_id, preferences)


@app.post("/api/digest-preferences")
async def api_save_digest_preferences(
    request: DigestPreferenceRequest,
    client_id: str = DEFAULT_CLIENT_ID,
):
    try:
        preferences = validate_preferences(request.model_dump(), require_email=request.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    digest_preference_store.save(preferences, client_id)
    return digest_preferences_response(client_id, preferences)


@app.post("/api/digest-preferences/unsubscribe")
async def api_unsubscribe_digest_preference(client_id: str, email: str, token: str):
    if not verify_unsubscribe_token(client_id, email, token):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe link.")
    preferences = digest_preference_store.get(client_id)
    if preferences.email.strip().lower() != email.strip().lower():
        raise HTTPException(status_code=404, detail="No matching digest preference was found.")
    preferences.enabled = False
    digest_preference_store.save(preferences, client_id)
    digest_preference_store.append_audit({
        "event": "unsubscribe",
        "client_id": client_id,
        "delivered": False,
        "mode": "preference",
        "reason": "disabled by unsubscribe link",
        "date": datetime.now().date().isoformat(),
        "recipient": preferences.email,
        "run_id": None,
    })
    return {"disabled": True, "preferences": preferences.to_dict()}


@app.post("/api/digest-deliveries/test")
async def api_test_digest_delivery(client_id: str = DEFAULT_CLIENT_ID):
    preferences = digest_preference_store.get(client_id)
    if not preferences.email:
        raise HTTPException(status_code=400, detail="Save an email address before sending a test digest.")
    scheduler = make_digest_scheduler()
    result = await scheduler.send_test(preferences, client_id)
    return {"results": [result.to_dict()]}


@app.post("/api/digest-deliveries/run")
async def api_run_digest_deliveries(
    now: str | None = None,
    run_id: str | None = None,
    scheduler_token: str | None = None,
    x_tidewindow_scheduler_token: Annotated[str | None, Header(alias="X-TideWindow-Scheduler-Token")] = None,
):
    require_scheduler_token(scheduler_token or x_tidewindow_scheduler_token)
    scheduler = make_digest_scheduler()
    run_at = None
    if now:
        try:
            run_at = datetime.fromisoformat(now)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="now must be an ISO datetime") from exc
    results = await scheduler.run_due(run_at, run_id=run_id)
    return {
        "run_id": results[0].run_id if results else run_id,
        "results": [result.to_dict() for result in results],
    }


@app.get("/api/digest-deliveries/audit")
async def api_digest_delivery_audit(limit: int = 50):
    return {"audit": digest_preference_store.audit(limit)}


@app.get("/api/digest-admin")
async def api_digest_admin(
    limit: int = 50,
    admin_token: str | None = None,
    x_tidewindow_admin_token: Annotated[str | None, Header(alias="X-TideWindow-Admin-Token")] = None,
):
    require_admin_token(admin_token or x_tidewindow_admin_token)
    preferences = digest_admin_preferences()
    audit = digest_preference_store.audit(limit)
    return {
        "preferences": preferences,
        "audit": audit,
        "readiness": digest_admin_readiness(),
        "health": digest_admin_health(preferences, audit),
    }


@app.post("/api/digest-admin/preferences/{client_id}")
async def api_update_digest_admin_preference(
    client_id: str,
    request: DigestAdminPreferenceRequest,
    admin_token: str | None = None,
    x_tidewindow_admin_token: Annotated[str | None, Header(alias="X-TideWindow-Admin-Token")] = None,
):
    require_admin_token(admin_token or x_tidewindow_admin_token)
    preferences = digest_preference_store.get(client_id)
    if not preferences.email:
        raise HTTPException(status_code=404, detail="No saved digest preference was found.")
    if request.enabled and not preferences.email:
        raise HTTPException(status_code=400, detail="A saved email address is required before enabling delivery.")
    preferences.enabled = request.enabled
    digest_preference_store.save(preferences, client_id)
    digest_preference_store.append_audit({
        "event": "preference_update",
        "client_id": client_id,
        "delivered": False,
        "mode": "admin",
        "reason": "enabled" if request.enabled else "disabled",
        "date": datetime.now().date().isoformat(),
        "recipient": preferences.email,
        "run_id": None,
    })
    return {"preferences": digest_admin_preferences()}


@app.post("/api/digest-admin/preferences/{client_id}/test")
async def api_test_digest_admin_preference(
    client_id: str,
    admin_token: str | None = None,
    x_tidewindow_admin_token: Annotated[str | None, Header(alias="X-TideWindow-Admin-Token")] = None,
):
    require_admin_token(admin_token or x_tidewindow_admin_token)
    return await api_test_digest_delivery(client_id)


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


def digest_preferences_response(client_id: str, preferences: DigestPreferences) -> dict:
    return {
        "client_id": client_id,
        "preferences": preferences.to_dict(),
        "options": {
            "activities": ["All", "Kayak", "Fish"],
            "density": ["compact", "standard", "full"],
            "risk": list(RISK_TOLERANCE_PROFILES.keys()),
        },
    }


def digest_admin_preferences() -> list[dict]:
    return [
        {
            "client_id": client_id,
            **preferences.to_dict(),
        }
        for client_id, preferences in sorted(digest_preference_store.all().items())
    ]


def digest_admin_readiness() -> dict:
    public_url = os.getenv("TIDEWINDOW_PUBLIC_URL", "").strip()
    signing_secret_set = bool(os.getenv("TIDEWINDOW_DIGEST_SIGNING_SECRET", "").strip())
    admin_token_set = bool(configured_admin_token())
    scheduler_token_set = bool(configured_scheduler_token())
    smtp_ready = smtp_configured()
    base_url = public_url or "http://127.0.0.1:8000"
    scheduler_token_suffix = "&scheduler_token=$TIDEWINDOW_SCHEDULER_TOKEN"
    checks = [
        {
            "id": "public_url",
            "label": "Public URL",
            "ok": bool(public_url),
            "detail": public_url or "Set TIDEWINDOW_PUBLIC_URL before hosted email delivery.",
        },
        {
            "id": "signing_secret",
            "label": "Signing secret",
            "ok": signing_secret_set,
            "detail": "Configured" if signing_secret_set else "Set TIDEWINDOW_DIGEST_SIGNING_SECRET so unsubscribe links stay stable.",
        },
        {
            "id": "admin_token",
            "label": "Admin token",
            "ok": admin_token_set,
            "detail": "Configured" if admin_token_set else "Set TIDEWINDOW_ADMIN_TOKEN before exposing /admin.",
        },
        {
            "id": "scheduler_token",
            "label": "Scheduler token",
            "ok": scheduler_token_set,
            "detail": "Configured" if scheduler_token_set else "Set TIDEWINDOW_SCHEDULER_TOKEN before enabling hosted cron.",
        },
        {
            "id": "email_provider",
            "label": "Email provider",
            "ok": smtp_ready,
            "detail": "SMTP configured" if smtp_ready else "Using local JSON outbox until SMTP env vars are configured.",
        },
        {
            "id": "preference_store",
            "label": "Preference store",
            "ok": path_writable(digest_preference_store.path),
            "detail": str(digest_preference_store.path),
        },
        {
            "id": "outbox",
            "label": "Outbox",
            "ok": path_writable(digest_email_sender.outbox_path),
            "detail": str(digest_email_sender.outbox_path),
        },
    ]
    return {
        "ready": all(check["ok"] for check in checks),
        "delivery_mode": "smtp" if smtp_ready else "local_outbox",
        "scheduler_command": f'curl -X POST "{base_url.rstrip("/")}/api/digest-deliveries/run?run_id=$(date +%Y%m%d%H%M%S){scheduler_token_suffix}"',
        "checks": checks,
    }


def configured_admin_token() -> str:
    return os.getenv("TIDEWINDOW_ADMIN_TOKEN", "").strip()


def configured_scheduler_token() -> str:
    return os.getenv("TIDEWINDOW_SCHEDULER_TOKEN", "").strip()


def require_admin_token(token: str | None) -> None:
    require_configured_token(configured_admin_token(), token, "Admin token is required.")


def require_scheduler_token(token: str | None) -> None:
    require_configured_token(configured_scheduler_token(), token, "Scheduler token is required.")


def require_configured_token(expected: str, provided: str | None, message: str) -> None:
    if not expected:
        return
    if not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail=message)


def path_writable(path: Path) -> bool:
    parent = path.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    return os.access(parent, os.W_OK)


def digest_admin_health(preferences: list[dict], audit: list[dict]) -> dict:
    today = datetime.now().date().isoformat()
    today_events = [entry for entry in audit if entry.get("date") == today]
    last_success = next((entry for entry in reversed(audit) if entry.get("delivered")), None)
    last_error = next((entry for entry in reversed(audit) if entry.get("mode") == "error"), None)
    last_run = next((entry for entry in reversed(audit) if entry.get("run_id")), None)
    return {
        "total_preferences": len(preferences),
        "enabled_preferences": sum(1 for preference in preferences if preference.get("enabled")),
        "today_delivered": sum(1 for entry in today_events if entry.get("delivered")),
        "today_skipped": sum(1 for entry in today_events if entry.get("mode") == "skipped"),
        "today_errors": sum(1 for entry in today_events if entry.get("mode") == "error"),
        "last_run_id": last_run.get("run_id") if last_run else None,
        "last_success_at": last_success.get("created_at") if last_success else None,
        "last_error": last_error.get("reason") if last_error else None,
    }


async def build_digest_for_preferences(preferences: DigestPreferences) -> dict:
    return await api_digest(**build_digest_params(preferences))


def make_digest_scheduler() -> DigestScheduler:
    return DigestScheduler(
        digest_preference_store,
        digest_email_sender,
        build_digest_for_preferences,
        public_base_url=os.getenv("TIDEWINDOW_PUBLIC_URL", ""),
    )


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


def normalize_digest_activity(activity: str) -> str:
    normalized = str(activity or "All").strip().lower()
    if normalized == "kayak":
        return "Kayak"
    if normalized in {"fish", "fishing"}:
        return "Fish"
    return "All"


def filter_digest_activity(digest: dict, activity: str) -> dict:
    selected = normalize_digest_activity(activity)
    tomorrow = digest.get("tomorrow", {})
    items = tomorrow.get("items", [])
    if selected != "All":
        items = [item for item in items if item.get("activity") == selected]

    if selected == "All":
        summary = tomorrow.get("summary", "")
    elif items:
        summary = f"Best tomorrow {selected.lower()} pick for the selected region."
    else:
        summary = f"No tomorrow {selected.lower()} recommendation is available yet."

    return {
        **digest,
        "tomorrow": {
            **tomorrow,
            "summary": summary,
            "items": items,
        },
    }


def build_digest_text(payload: dict) -> str:
    region = payload["config"]["region"]["name"]
    risk = payload["config"]["risk_tolerance"]["id"]
    tomorrow = payload["digest"].get("tomorrow", {})
    lines = [
        f"TideWindow Tomorrow's Best - {region}",
        f"{tomorrow.get('label', 'Tomorrow')} | {risk} risk",
    ]
    for item in tomorrow.get("items", []):
        lines.extend(
            [
                "",
                f"{item['activity']}: {item['zone_title']}",
                f"{_compact_time(item['start'])}-{_compact_time(item['end'])} | {item['status']} | {item['phase']}",
                f"{item['current']:.1f} kt current | {item['wind']:.0f} kt wind | {item['tide']:.1f} ft tide",
                item["why"],
                item["note"],
            ]
        )
    if not tomorrow.get("items"):
        lines.append(tomorrow.get("summary", "No tomorrow recommendations are available yet."))
    return "\n".join(line for line in lines if line is not None)


def build_digest_ics(payload: dict) -> str:
    region_id = payload["config"]["region"]["id"]
    region_name = payload["config"]["region"]["name"]
    items = payload["digest"].get("tomorrow", {}).get("items", [])
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//TideWindow//Tomorrow Digest//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for item in items:
        start = _as_datetime(item["start"])
        end = _as_datetime(item["end"])
        summary = f"TideWindow {item['activity']}: {item['zone_title']}"
        uid = f"tidewindow-{region_id}-{item['activity'].lower()}-{start.strftime('%Y%m%dT%H%M%S')}@tidewindow"
        description = "\\n".join(
            [
                item["why"],
                item["note"],
                f"{item['current']:.1f} kt current, {item['wind']:.0f} kt wind, {item['tide']:.1f} ft tide.",
            ]
        )
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_ics_escape(uid)}",
                f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{_ics_escape(summary)}",
                f"LOCATION:{_ics_escape(region_name)}",
                f"DESCRIPTION:{_ics_escape(description)}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _compact_time(value: datetime | str) -> str:
    parsed = _as_datetime(value)
    hour = parsed.strftime("%I").lstrip("0") or "0"
    return f"{hour}:{parsed.strftime('%M %p')}"


def _as_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _ics_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
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
