import asyncio
import unittest
from datetime import datetime, timedelta

import web_app
from marine_cache import MarineStateCache
from marine_config import ALL_ZONES, FORECAST_HOURS, OPTIONAL_ZONES, WEB_REFRESH_INTERVAL_SECONDS, ZONES
from marine_regions import BREMERTON_TIDE_STATION, DEFAULT_REGION_ID, REGIONS, zone_configs_for_region


def live_telemetry():
    return {
        "current_knots": 1.1,
        "tide_feet": 5.2,
        "wind_knots": 4.0,
        "sources": {"tide": "live", "current": "predicted", "wind": "live"},
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
        for hour in range(8)
    ]
    return {
        "predictions": predictions,
        "wind_predictions": [
            {"time": point["time"], "wind_knots": 4.0} for point in predictions
        ],
        "current_predictions": [
            {"time": point["time"], "speed": 1.0 + index * 0.1, "dir": 150.0}
            for index, point in enumerate(predictions)
        ],
        "sources": {"tide": "live", "current": "predicted", "wind": "live"},
        "fallback_reason": None,
        "wind_fallback_reason": None,
    }


def seed_forecast():
    return {
        "predictions": [],
        "wind_predictions": [],
        "current_predictions": [],
        "sources": {"tide": "seed", "current": "derived", "wind": "fallback"},
        "fallback_reason": "forecast unavailable",
        "wind_fallback_reason": "fallback",
    }


class StubClient:
    def __init__(self, telemetry, forecast):
        self._telemetry = telemetry
        self._forecast = forecast

    async def fetch_telemetry(self):
        return self._telemetry

    async def fetch_forecast(self):
        return self._forecast


class CountingClient(StubClient):
    calls = {"telemetry": 0, "forecast": 0}

    async def fetch_telemetry(self):
        CountingClient.calls["telemetry"] += 1
        return self._telemetry

    async def fetch_forecast(self):
        CountingClient.calls["forecast"] += 1
        return self._forecast


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self._original_cache = web_app.state_cache
        self._original_region_caches = dict(web_app.region_state_caches)

    def tearDown(self):
        web_app.state_cache = self._original_cache
        web_app.region_state_caches.clear()
        web_app.region_state_caches.update(self._original_region_caches)

    def _use_cache(self, factory, ttl=WEB_REFRESH_INTERVAL_SECONDS):
        cache = MarineStateCache(ttl, factory)
        web_app.state_cache = cache
        return cache

    def test_api_state_returns_json_ready_dashboard_payload(self):
        self._use_cache(lambda: StubClient(live_telemetry(), live_forecast()))
        payload = asyncio.run(web_app.api_state())

        self.assertEqual(len(payload["zones"]), len(ALL_ZONES))
        self.assertEqual(
            [zone["id"] for zone in payload["zones"]],
            list(zone_configs_for_region(DEFAULT_REGION_ID).keys()),
        )
        self.assertEqual(
            sum(1 for zone in payload["zones"] if zone["active_by_default"]),
            len(ZONES),
        )
        self.assertEqual(
            sum(1 for zone in payload["zones"] if not zone["active_by_default"]),
            len(OPTIONAL_ZONES),
        )
        self.assertEqual(payload["config"]["app"], "TideWindow")
        self.assertEqual(payload["config"]["forecast_hours"], FORECAST_HOURS)
        self.assertIn("generated_at", payload)
        self.assertIn("confidence", payload)
        self.assertGreater(len(payload["windows"]), 0)
        self.assertGreater(len(payload["timeline"]), 0)
        self.assertIsInstance(payload["windows"][0]["start"], str)
        self.assertIsInstance(payload["timeline"][0]["start"], str)
        self.assertIn("map", payload["zones"][0])
        self.assertEqual(payload["zones"][0]["map"]["lat"], ALL_ZONES[payload["zones"][0]["id"]]["lat"])
        self.assertEqual(payload["zones"][0]["map"]["lon"], ALL_ZONES[payload["zones"][0]["id"]]["lon"])
        self.assertIsInstance(payload["forecast"]["predictions"][0]["time"], str)
        self.assertIsInstance(payload["forecast"]["wind_predictions"][0]["time"], str)
        self.assertIsInstance(payload["forecast"]["current_predictions"][0]["time"], str)
        self.assertEqual(payload["windows"][0]["current_source"], "predicted")
        self.assertEqual(payload["timeline"][0]["current_source"], "predicted")

    def test_api_regions_returns_region_picker_metadata(self):
        payload = asyncio.run(web_app.api_regions())

        self.assertEqual(payload["default_region"], DEFAULT_REGION_ID)
        self.assertEqual(payload["regions"][0]["id"], DEFAULT_REGION_ID)
        self.assertEqual(payload["regions"][0]["name"], "Gig Harbor")
        self.assertEqual(payload["regions"][0]["default_spot_limit"], 10)
        self.assertEqual(payload["regions"][0]["spot_count"], len(ALL_ZONES))
        self.assertEqual(len(payload["regions"]), len(REGIONS))
        self.assertIn("port_orchard", {region["id"] for region in payload["regions"]})
        self.assertIn("bremerton", {region["id"] for region in payload["regions"]})
        self.assertIn("silverdale", {region["id"] for region in payload["regions"]})
        self.assertIn("chico", {region["id"] for region in payload["regions"]})
        self.assertIn("gorst", {region["id"] for region in payload["regions"]})

    def test_api_state_can_limit_region_spots(self):
        self._use_cache(lambda: StubClient(live_telemetry(), live_forecast()))
        payload = asyncio.run(web_app.api_state(region=DEFAULT_REGION_ID, limit=10))

        self.assertEqual(len(payload["zones"]), 10)
        self.assertEqual(payload["config"]["region"]["id"], DEFAULT_REGION_ID)
        self.assertEqual(payload["config"]["region"]["visible_spot_limit"], 10)
        self.assertEqual(
            payload["config"]["region"]["provider_context"]["tide_station"],
            "9446484",
        )
        self.assertEqual(
            [zone["id"] for zone in payload["zones"]],
            list(zone_configs_for_region(DEFAULT_REGION_ID, limit=10).keys()),
        )
        returned_ids = {zone["id"] for zone in payload["zones"]}
        self.assertTrue(all(window["zone_id"] in returned_ids for window in payload["windows"]))
        self.assertTrue(all(set(item["zones"]).issubset(returned_ids) for item in payload["timeline"]))

    def test_api_state_uses_region_scoped_cache_and_provider_context(self):
        cache = self._use_cache(lambda: StubClient(live_telemetry(), live_forecast()))
        web_app.region_state_caches["port_orchard"] = cache

        payload = asyncio.run(web_app.api_state(region="port_orchard", limit=10))

        self.assertEqual(payload["config"]["region"]["id"], "port_orchard")
        self.assertEqual(payload["config"]["region"]["provider_context"]["tide_station"], BREMERTON_TIDE_STATION)
        self.assertEqual(payload["config"]["region"]["provider_context"]["current_station"], "PUG1514")
        self.assertEqual(len(payload["zones"]), 10)
        self.assertEqual(
            [zone["id"] for zone in payload["zones"]],
            list(zone_configs_for_region("port_orchard", limit=10).keys()),
        )

    def test_api_state_includes_cache_metadata_and_data_age(self):
        self._use_cache(lambda: StubClient(live_telemetry(), live_forecast()))
        payload = asyncio.run(web_app.api_state())

        self.assertIn("cache", payload)
        self.assertFalse(payload["cache"]["served_from_cache"])
        self.assertFalse(payload["cache"]["telemetry_stale"])
        self.assertFalse(payload["cache"]["forecast_stale"])

        telemetry = payload["telemetry"]
        self.assertIn("observed_at", telemetry)
        self.assertIn("age_seconds", telemetry)
        self.assertFalse(telemetry["stale"])
        self.assertIsInstance(payload["forecast"]["age_seconds"], int)

    def test_api_state_serves_cached_payload_within_ttl(self):
        CountingClient.calls = {"telemetry": 0, "forecast": 0}
        self._use_cache(
            lambda: CountingClient(live_telemetry(), live_forecast()),
            ttl=9999,
        )

        first = asyncio.run(web_app.api_state())
        second = asyncio.run(web_app.api_state())

        # Upstream is only hit once; the second request is served from cache.
        self.assertEqual(CountingClient.calls["telemetry"], 1)
        self.assertEqual(CountingClient.calls["forecast"], 1)
        self.assertFalse(first["cache"]["served_from_cache"])
        self.assertTrue(second["cache"]["served_from_cache"])

    def test_api_state_serves_last_good_when_upstream_degrades(self):
        mode = {"live": True}

        def factory():
            if mode["live"]:
                return StubClient(live_telemetry(), live_forecast())
            return StubClient(seed_telemetry(), seed_forecast())

        cache = self._use_cache(factory, ttl=9999)

        good = asyncio.run(web_app.api_state())
        self.assertFalse(good["cache"]["telemetry_stale"])

        # Upstream degrades to seed and the TTL expires.
        mode["live"] = False
        cache._fetched_monotonic -= 10_000

        degraded = asyncio.run(web_app.api_state())
        self.assertTrue(degraded["cache"]["telemetry_stale"])
        self.assertTrue(degraded["cache"]["forecast_stale"])
        # The last good live reading is served instead of seed.
        self.assertEqual(degraded["telemetry"]["sources"]["tide"], "live")
        self.assertTrue(degraded["telemetry"]["stale"])
        self.assertGreater(len(degraded["windows"]), 0)

    def test_health_returns_lightweight_status_payload(self):
        payload = asyncio.run(web_app.health())

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["app"], "TideWindow")
        self.assertEqual(payload["zones"], len(ALL_ZONES))
        self.assertEqual(payload["default_zones"], len(ZONES))
        self.assertEqual(payload["optional_zones"], len(OPTIONAL_ZONES))
        self.assertEqual(payload["regions"], len(REGIONS))
        self.assertIn("generated_at", payload)
        self.assertIn("providers", payload)
        self.assertIn("noaa_tide_station", payload["providers"])
        self.assertEqual(len(payload["providers"]["regions"]), len(REGIONS))
        self.assertIn(
            {"id": "port_orchard", "tide_station": BREMERTON_TIDE_STATION, "current_station": "PUG1514", "nws_zone": "PZZ135"},
            payload["providers"]["regions"],
        )


if __name__ == "__main__":
    unittest.main()
