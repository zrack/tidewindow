import asyncio
import unittest
from datetime import datetime, timedelta

from marine_cache import MarineStateCache, forecast_is_live, telemetry_is_live


def live_telemetry(tide=5.0):
    return {
        "current_knots": 1.0,
        "tide_feet": tide,
        "wind_knots": 4.0,
        "sources": {"tide": "live", "current": "live", "wind": "live"},
        "fallback_reason": None,
        "updated_at": "now",
    }


def seed_telemetry():
    return {
        "current_knots": 1.85,
        "tide_feet": 5.4,
        "wind_knots": 6.5,
        "sources": {"tide": "seed", "current": "seed", "wind": "seed"},
        "fallback_reason": "telemetry fetch failed",
        "updated_at": "now",
    }


def live_forecast():
    start = datetime(2026, 5, 30, 10)
    predictions = [
        {"time": start + timedelta(hours=hour), "tide_feet": 4.0 + hour * 0.3}
        for hour in range(4)
    ]
    return {
        "predictions": predictions,
        "wind_predictions": [],
        "sources": {"tide": "live", "current": "derived", "wind": "fallback"},
        "fallback_reason": None,
        "wind_fallback_reason": None,
    }


def seed_forecast():
    return {
        "predictions": [],
        "wind_predictions": [],
        "sources": {"tide": "seed", "current": "derived", "wind": "fallback"},
        "fallback_reason": "forecast unavailable",
        "wind_fallback_reason": "fallback",
    }


class ScriptedClient:
    """Returns the telemetry/forecast pair currently set on the shared box."""

    def __init__(self, box):
        self.box = box
        box["telemetry_calls"] = box.get("telemetry_calls", 0)
        box["forecast_calls"] = box.get("forecast_calls", 0)

    async def fetch_telemetry(self):
        self.box["telemetry_calls"] += 1
        return self.box["telemetry"]

    async def fetch_forecast(self):
        self.box["forecast_calls"] += 1
        return self.box["forecast"]


class LivenessTests(unittest.TestCase):
    def test_liveness_detection(self):
        self.assertTrue(telemetry_is_live(live_telemetry()))
        self.assertFalse(telemetry_is_live(seed_telemetry()))
        self.assertTrue(forecast_is_live(live_forecast()))
        self.assertFalse(forecast_is_live(seed_forecast()))


class CacheTests(unittest.TestCase):
    def test_caches_within_ttl_without_refetching(self):
        box = {"telemetry": live_telemetry(), "forecast": live_forecast()}
        cache = MarineStateCache(ttl_seconds=9999, client_factory=lambda: ScriptedClient(box))

        async def run():
            first = await cache.get()
            second = await cache.get()
            return first, second

        (tel1, _, meta1), (tel2, _, meta2) = asyncio.run(run())

        self.assertEqual(box["telemetry_calls"], 1)
        self.assertEqual(box["forecast_calls"], 1)
        self.assertFalse(meta1["served_from_cache"])
        self.assertTrue(meta2["served_from_cache"])
        self.assertFalse(tel1["stale"])
        self.assertFalse(tel2["stale"])

    def test_serves_last_good_when_fresh_fetch_fails(self):
        box = {"telemetry": live_telemetry(tide=7.7), "forecast": live_forecast()}
        cache = MarineStateCache(ttl_seconds=9999, client_factory=lambda: ScriptedClient(box))

        async def run():
            good = await cache.get()
            box["telemetry"] = seed_telemetry()
            box["forecast"] = seed_forecast()
            # Force the TTL to expire so the next get() refetches upstream.
            cache._fetched_monotonic -= 10_000
            degraded = await cache.get()
            return good, degraded

        (good_tel, good_fc, good_meta), (stale_tel, stale_fc, stale_meta) = asyncio.run(run())

        self.assertFalse(good_meta["telemetry_stale"])
        self.assertFalse(good_meta["forecast_stale"])

        # The degraded fetch returned seed, but the cache serves the last good reading.
        self.assertTrue(stale_meta["telemetry_stale"])
        self.assertTrue(stale_meta["forecast_stale"])
        self.assertEqual(stale_tel["tide_feet"], 7.7)
        self.assertTrue(stale_tel["stale"])
        self.assertEqual(len(stale_fc["predictions"]), len(good_fc["predictions"]))
        self.assertIn("age_seconds", stale_tel)
        self.assertIn("observed_at", stale_tel)


if __name__ == "__main__":
    unittest.main()
