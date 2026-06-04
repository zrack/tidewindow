"""Server-side caching and last-good fallback for TideWindow marine state.

Sits between the web layer and ``NoaaMarineClient`` so that:

* repeated requests within a TTL reuse the last upstream fetch instead of
  hitting NOAA/OpenWeather again (cache + stale-while-revalidate), and
* when a fresh fetch fails and falls back to seed data, the last *good*
  reading is served instead, annotated with its age so the UI can say so.
"""

import asyncio
import time
from datetime import datetime


def telemetry_is_live(telemetry: dict | None) -> bool:
    """True when telemetry reflects a real NOAA reading, not seed/fallback."""
    if not telemetry or telemetry.get("fallback_reason"):
        return False
    return telemetry.get("sources", {}).get("tide") == "live"


def forecast_is_live(forecast: dict | None) -> bool:
    """True when the forecast reflects real NOAA predictions, not seed."""
    if not forecast or forecast.get("fallback_reason"):
        return False
    return forecast.get("sources", {}).get("tide") == "live"


class MarineStateCache:
    """Caches upstream telemetry/forecast with TTL and last-good fallback."""

    def __init__(self, ttl_seconds, client_factory):
        self.ttl = max(15.0, float(ttl_seconds))
        self._client_factory = client_factory
        self._lock = asyncio.Lock()

        self._fetched_monotonic = None

        self._telemetry = None
        self._telemetry_observed_at = None
        self._telemetry_stale = False
        self._last_good_telemetry = None
        self._last_good_telemetry_at = None

        self._forecast = None
        self._forecast_observed_at = None
        self._forecast_stale = False
        self._last_good_forecast = None
        self._last_good_forecast_at = None

    def _fresh(self) -> bool:
        return (
            self._telemetry is not None
            and self._fetched_monotonic is not None
            and (time.monotonic() - self._fetched_monotonic) < self.ttl
        )

    async def get(self) -> tuple[dict, dict, dict]:
        """Returns ``(telemetry, forecast, cache_meta)``, refreshing if stale.

        ``telemetry`` and ``forecast`` are copies annotated with
        ``observed_at`` (ISO), ``age_seconds`` (int) and ``stale`` (bool).
        """
        if self._fresh():
            return self._snapshot(served_from_cache=True)

        async with self._lock:
            # Another request may have refreshed while we waited for the lock.
            if self._fresh():
                return self._snapshot(served_from_cache=True)
            await self._refresh()
            return self._snapshot(served_from_cache=False)

    async def _refresh(self) -> None:
        client = self._client_factory()
        telemetry, forecast = await asyncio.gather(
            client.fetch_telemetry(),
            client.fetch_forecast(),
        )
        now = datetime.now()

        if telemetry_is_live(telemetry):
            self._last_good_telemetry = telemetry
            self._last_good_telemetry_at = now
            self._telemetry = telemetry
            self._telemetry_observed_at = now
            self._telemetry_stale = False
        elif self._last_good_telemetry is not None:
            self._telemetry = self._last_good_telemetry
            self._telemetry_observed_at = self._last_good_telemetry_at
            self._telemetry_stale = True
        else:
            self._telemetry = telemetry
            self._telemetry_observed_at = now
            self._telemetry_stale = False

        if forecast_is_live(forecast):
            self._last_good_forecast = forecast
            self._last_good_forecast_at = now
            self._forecast = forecast
            self._forecast_observed_at = now
            self._forecast_stale = False
        elif self._last_good_forecast is not None:
            self._forecast = self._last_good_forecast
            self._forecast_observed_at = self._last_good_forecast_at
            self._forecast_stale = True
        else:
            self._forecast = forecast
            self._forecast_observed_at = now
            self._forecast_stale = False

        self._fetched_monotonic = time.monotonic()

    def _snapshot(self, served_from_cache: bool) -> tuple[dict, dict, dict]:
        now = datetime.now()

        telemetry = dict(self._telemetry)
        telemetry_age = max(0, int((now - self._telemetry_observed_at).total_seconds()))
        telemetry["observed_at"] = self._telemetry_observed_at.isoformat(timespec="seconds")
        telemetry["age_seconds"] = telemetry_age
        telemetry["stale"] = self._telemetry_stale

        forecast = dict(self._forecast)
        forecast_age = max(0, int((now - self._forecast_observed_at).total_seconds()))
        forecast["observed_at"] = self._forecast_observed_at.isoformat(timespec="seconds")
        forecast["age_seconds"] = forecast_age
        forecast["stale"] = self._forecast_stale

        meta = {
            "served_from_cache": served_from_cache,
            "ttl_seconds": int(self.ttl),
            "age_seconds": max(0, int(time.monotonic() - self._fetched_monotonic)),
            "telemetry_stale": self._telemetry_stale,
            "forecast_stale": self._forecast_stale,
        }
        return telemetry, forecast, meta
