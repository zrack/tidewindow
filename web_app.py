import asyncio
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from marine_config import (
    ALL_ZONES,
    FORECAST_HOURS,
    NOAA_CURRENT_STATION,
    NOAA_TIDE_STATION,
    OPTIONAL_ZONES,
    WEB_APP_NAME,
    WEB_REFRESH_INTERVAL_SECONDS,
    ZONES,
)
from marine_engine import MarineSafetyEngine
from noaa_client import NoaaMarineClient


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
APP_VERSION = "0.1.0"

app = FastAPI(title=WEB_APP_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


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
        "forecast_hours": FORECAST_HOURS,
        "refresh_seconds": WEB_REFRESH_INTERVAL_SECONDS,
        "providers": {
            "noaa_tide_station": NOAA_TIDE_STATION,
            "noaa_current_station": NOAA_CURRENT_STATION,
            "openweather": "configured" if os.getenv("OPENWEATHER_API_KEY") else "optional_missing",
        },
    }


@app.get("/api/state")
async def api_state():
    client = NoaaMarineClient()
    engine = MarineSafetyEngine()
    telemetry, forecast = await asyncio.gather(
        client.fetch_telemetry(),
        client.fetch_forecast(),
    )

    zones = engine.get_zone_telemetry(
        telemetry["current_knots"],
        telemetry["tide_feet"],
        telemetry["wind_knots"],
        zones_config=ALL_ZONES,
    )
    zone_cards = []
    for zone_id, zone_config in ALL_ZONES.items():
        zone_data = zones[zone_id]
        kayak = engine.evaluate_kayaking(
            zone_id,
            zone_data["current"],
            zone_data["wind"],
        )
        fish = engine.evaluate_fly_fishing(
            zone_id,
            zone_data["current"],
            zone_data["tide"],
        )
        zone_cards.append(
            {
                "id": zone_id,
                "title": zone_config["title"],
                "active_by_default": zone_id in ZONES,
                "map": {
                    "lat": zone_config.get("lat"),
                    "lon": zone_config.get("lon"),
                },
                "current": round(zone_data["current"], 2),
                "wind": round(zone_data["wind"], 1),
                "tide": round(zone_data["tide"], 1),
                "kayak": kayak,
                "fish": fish,
            }
        )

    windows = engine.build_forecast_windows(
        forecast.get("predictions", []),
        telemetry["wind_knots"],
        wind_predictions=forecast.get("wind_predictions", []),
        wind_source=forecast.get("sources", {}).get("wind", "fallback"),
        zones_config=ALL_ZONES,
    )
    timeline = engine.build_hourly_timeline(
        forecast.get("predictions", []),
        telemetry["wind_knots"],
        wind_predictions=forecast.get("wind_predictions", []),
        wind_source=forecast.get("sources", {}).get("wind", "fallback"),
        zones_config=ALL_ZONES,
    )
    confidence = engine.evaluate_confidence(
        telemetry,
        forecast,
        telemetry["wind_knots"],
    )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": {
            "app": WEB_APP_NAME,
            "refresh_seconds": WEB_REFRESH_INTERVAL_SECONDS,
            "forecast_hours": FORECAST_HOURS,
        },
        "telemetry": telemetry,
        "forecast": {
            **forecast,
            "predictions": _serialize_points(forecast.get("predictions", [])),
            "wind_predictions": _serialize_points(forecast.get("wind_predictions", [])),
        },
        "zones": zone_cards,
        "windows": [_serialize_window(window) for window in windows],
        "timeline": [_serialize_window(window) for window in timeline],
        "confidence": confidence,
    }


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
