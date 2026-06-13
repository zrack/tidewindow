import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import web_app
from digest_delivery import DigestEmailSender, DigestPreferenceStore, sign_unsubscribe_token
from marine_cache import MarineStateCache
from marine_config import ALL_ZONES, FORECAST_HOURS, OPTIONAL_ZONES, WEB_REFRESH_INTERVAL_SECONDS, ZONES
from marine_regions import BREMERTON_TIDE_STATION, DEFAULT_REGION_ID, REGIONS, zone_configs_for_region


def live_telemetry():
    return {
        "current_knots": 1.1,
        "tide_feet": 5.2,
        "wind_knots": 4.0,
        "wind_direction": 190.0,
        "sources": {"tide": "live", "current": "predicted", "wind": "live"},
        "fallback_reason": None,
        "updated_at": "now",
    }


def seed_telemetry():
    return {
        "current_knots": 1.85,
        "tide_feet": 5.4,
        "wind_knots": 6.5,
        "wind_direction": None,
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
            {"time": point["time"], "wind_knots": 4.0, "wind_direction": 190.0}
            for point in predictions
        ],
        "current_predictions": [
            {"time": point["time"], "speed": 1.0 + index * 0.1, "dir": 150.0}
            for index, point in enumerate(predictions)
        ],
        "sources": {"tide": "live", "current": "predicted", "wind": "live"},
        "fallback_reason": None,
        "wind_fallback_reason": None,
    }


def tomorrow_forecast():
    start = (datetime.now() + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
    predictions = [
        {"time": start + timedelta(hours=hour), "tide_feet": 4.0 + hour * 0.4}
        for hour in range(10)
    ]
    return {
        "predictions": predictions,
        "wind_predictions": [
            {"time": point["time"], "wind_knots": 5.0, "wind_direction": 190.0}
            for point in predictions
        ],
        "current_predictions": [
            {"time": point["time"], "speed": 0.8 + index * 0.1, "dir": 150.0}
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
        self._original_digest_store = web_app.digest_preference_store
        self._original_digest_sender = web_app.digest_email_sender

    def tearDown(self):
        web_app.state_cache = self._original_cache
        web_app.region_state_caches.clear()
        web_app.region_state_caches.update(self._original_region_caches)
        web_app.digest_preference_store = self._original_digest_store
        web_app.digest_email_sender = self._original_digest_sender

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
        self.assertEqual(payload["zones"][0]["wind_direction"], 190.0)
        self.assertIn(payload["zones"][0]["wind_exposure"], {"exposed", "partial", "sheltered"})
        self.assertEqual(payload["windows"][0]["wind_direction"], 190.0)
        self.assertEqual(payload["timeline"][0]["zones"][payload["zones"][0]["id"]]["wind_direction"], 190.0)

    def test_api_regions_returns_region_picker_metadata(self):
        payload = asyncio.run(web_app.api_regions())

        self.assertEqual(payload["default_region"], DEFAULT_REGION_ID)
        self.assertEqual(payload["regions"][0]["id"], DEFAULT_REGION_ID)
        self.assertEqual(payload["regions"][0]["name"], "Gig Harbor")
        self.assertEqual(payload["regions"][0]["default_spot_limit"], len(ALL_ZONES))
        self.assertEqual(payload["regions"][0]["spot_count"], len(ALL_ZONES))
        self.assertEqual(len(payload["regions"]), len(REGIONS))
        self.assertIn("port_orchard", {region["id"] for region in payload["regions"]})
        self.assertIn("bremerton", {region["id"] for region in payload["regions"]})
        self.assertIn("silverdale", {region["id"] for region in payload["regions"]})
        self.assertIn("tacoma_narrows", {region["id"] for region in payload["regions"]})
        self.assertIn("carr_inlet", {region["id"] for region in payload["regions"]})
        self.assertIn("case_inlet", {region["id"] for region in payload["regions"]})
        self.assertIn("anderson_island", {region["id"] for region in payload["regions"]})
        self.assertIn("steilacoom_nisqually", {region["id"] for region in payload["regions"]})
        self.assertIn("olympia_budd_inlet", {region["id"] for region in payload["regions"]})
        self.assertIn("south_hood_canal", {region["id"] for region in payload["regions"]})
        self.assertIn("aberdeen", {region["id"] for region in payload["regions"]})
        self.assertNotIn("chico", {region["id"] for region in payload["regions"]})
        self.assertNotIn("gorst", {region["id"] for region in payload["regions"]})
        aliases = {entry["normalized"]: entry for entry in payload["search_aliases"]}
        self.assertEqual(aliases["port orchard"]["region_id"], "port_orchard")
        self.assertEqual(aliases["aberdeen"]["region_id"], "aberdeen")
        self.assertEqual(aliases["belfair"]["region_id"], "south_hood_canal")
        self.assertEqual(aliases["chico"]["region_id"], "silverdale")
        self.assertIn("Using South Hood Canal", aliases["belfair"]["note"])

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

    def test_api_state_defaults_to_all_region_spots(self):
        self._use_cache(lambda: StubClient(live_telemetry(), live_forecast()))
        payload = asyncio.run(web_app.api_state(region=DEFAULT_REGION_ID))

        self.assertEqual(len(payload["zones"]), len(ALL_ZONES))
        self.assertEqual(payload["config"]["region"]["visible_spot_limit"], len(ALL_ZONES))
        self.assertEqual(
            [zone["id"] for zone in payload["zones"]],
            list(zone_configs_for_region(DEFAULT_REGION_ID).keys()),
        )

    def test_api_state_includes_tomorrow_best_window_digest(self):
        self._use_cache(lambda: StubClient(live_telemetry(), tomorrow_forecast()))
        payload = asyncio.run(web_app.api_state(region=DEFAULT_REGION_ID, limit=10))

        digest = payload["digest"]["tomorrow"]
        activities = {item["activity"] for item in digest["items"]}
        self.assertEqual(digest["label"], "Tomorrow")
        self.assertEqual(activities, {"Kayak", "Fish"})
        self.assertIn("tomorrow", digest["summary"].lower())
        for item in digest["items"]:
            with self.subTest(activity=item["activity"]):
                self.assertIn(item["zone_id"], zone_configs_for_region(DEFAULT_REGION_ID, limit=10))
                self.assertIsInstance(item["start"], str)
                self.assertIsInstance(item["end"], str)
                self.assertIn("why", item)
                self.assertIn("standard risk thresholds", item["why"])
                self.assertIn("current", item)
                self.assertIn("wind", item)
                self.assertIn("tide", item)

    def test_api_digest_filters_activity_and_returns_copy_text(self):
        self._use_cache(lambda: StubClient(live_telemetry(), tomorrow_forecast()))
        payload = asyncio.run(web_app.api_digest(region=DEFAULT_REGION_ID, limit=10, activity="Kayak"))

        digest = payload["digest"]["tomorrow"]
        self.assertEqual(payload["activity"], "Kayak")
        self.assertEqual({item["activity"] for item in digest["items"]}, {"Kayak"})
        self.assertIn("Best tomorrow kayak", digest["summary"])
        self.assertIn("TideWindow Tomorrow's Best", payload["text"])
        self.assertIn("Kayak:", payload["text"])
        self.assertNotIn("Fish:", payload["text"])

    def test_api_digest_calendar_exports_filtered_events(self):
        self._use_cache(lambda: StubClient(live_telemetry(), tomorrow_forecast()))
        response = asyncio.run(web_app.api_digest_ics(region=DEFAULT_REGION_ID, limit=10, activity="Fish"))
        body = response.body.decode("utf-8")

        self.assertIn("text/calendar", response.media_type)
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertIn("BEGIN:VEVENT", body)
        self.assertIn("SUMMARY:TideWindow Fish:", body)
        self.assertNotIn("SUMMARY:TideWindow Kayak:", body)
        self.assertIn("END:VCALENDAR", body)

    def test_digest_preferences_can_be_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            request = web_app.DigestPreferenceRequest(
                enabled=True,
                email="test@example.com",
                delivery_time="06:45",
                region=DEFAULT_REGION_ID,
                activity="Kayak",
                risk="standard",
                density="compact",
            )

            saved = asyncio.run(web_app.api_save_digest_preferences(request, client_id="phone"))
            loaded = asyncio.run(web_app.api_digest_preferences(client_id="phone"))

            self.assertEqual(saved["preferences"]["email"], "test@example.com")
            self.assertTrue(loaded["preferences"]["enabled"])
            self.assertEqual(loaded["preferences"]["activity"], "Kayak")
            self.assertEqual(loaded["options"]["activities"], ["All", "Kayak", "Fish"])

    def test_test_digest_delivery_queues_outbox_message(self):
        self._use_cache(lambda: StubClient(live_telemetry(), tomorrow_forecast()))
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            web_app.digest_email_sender = DigestEmailSender(Path(temp_dir) / "outbox.json", smtp_enabled=False)
            request = web_app.DigestPreferenceRequest(
                enabled=True,
                email="test@example.com",
                delivery_time="06:45",
                region=DEFAULT_REGION_ID,
                activity="Fish",
                risk="standard",
                density="compact",
            )
            asyncio.run(web_app.api_save_digest_preferences(request, client_id="phone"))

            payload = asyncio.run(web_app.api_test_digest_delivery(client_id="phone"))

            self.assertTrue(payload["results"][0]["delivered"])
            self.assertEqual(payload["results"][0]["mode"], "outbox")
            self.assertEqual(payload["results"][0]["client_id"], "phone")
            audit = asyncio.run(web_app.api_digest_delivery_audit())
            self.assertEqual(audit["audit"][0]["event"], "test_delivery")

    def test_unsubscribe_link_disables_saved_digest_preference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            request = web_app.DigestPreferenceRequest(
                enabled=True,
                email="test@example.com",
                delivery_time="06:45",
                region=DEFAULT_REGION_ID,
                activity="Fish",
                risk="standard",
                density="compact",
            )
            asyncio.run(web_app.api_save_digest_preferences(request, client_id="phone"))
            token = sign_unsubscribe_token("phone", "test@example.com")

            payload = asyncio.run(web_app.api_unsubscribe_digest_preference(
                client_id="phone",
                email="test@example.com",
                token=token,
            ))
            loaded = asyncio.run(web_app.api_digest_preferences(client_id="phone"))
            audit = asyncio.run(web_app.api_digest_delivery_audit())

            self.assertTrue(payload["disabled"])
            self.assertFalse(loaded["preferences"]["enabled"])
            self.assertEqual(audit["audit"][0]["event"], "unsubscribe")

    def test_digest_admin_lists_preferences_and_audit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            request = web_app.DigestPreferenceRequest(
                enabled=True,
                email="admin@example.com",
                delivery_time="06:45",
                region=DEFAULT_REGION_ID,
                activity="Fish",
                risk="standard",
                density="compact",
            )
            asyncio.run(web_app.api_save_digest_preferences(request, client_id="admin-phone"))
            web_app.digest_preference_store.append_audit({
                "event": "delivery",
                "client_id": "admin-phone",
                "delivered": True,
                "mode": "outbox",
                "reason": "queued",
                "date": "2026-06-13",
                "recipient": "admin@example.com",
                "run_id": "admin-run",
            })

            payload = asyncio.run(web_app.api_digest_admin())

            self.assertEqual(payload["preferences"][0]["client_id"], "admin-phone")
            self.assertEqual(payload["preferences"][0]["email"], "admin@example.com")
            self.assertEqual(payload["audit"][0]["run_id"], "admin-run")

    def test_digest_admin_reports_scheduler_readiness(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            web_app.digest_email_sender = DigestEmailSender(Path(temp_dir) / "outbox.json", smtp_enabled=False)
            env = {
                **os.environ,
                "TIDEWINDOW_PUBLIC_URL": "https://tidewindow.example",
                "TIDEWINDOW_DIGEST_SIGNING_SECRET": "test-secret",
                "TIDEWINDOW_SMTP_HOST": "smtp.example.com",
                "TIDEWINDOW_SMTP_FROM": "digest@example.com",
            }
            with patch.dict(os.environ, env, clear=True):
                payload = asyncio.run(web_app.api_digest_admin())

            readiness = payload["readiness"]
            self.assertTrue(readiness["ready"])
            self.assertEqual(readiness["delivery_mode"], "smtp")
            self.assertIn("https://tidewindow.example/api/digest-deliveries/run", readiness["scheduler_command"])

    def test_digest_admin_can_disable_saved_preference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            request = web_app.DigestPreferenceRequest(
                enabled=True,
                email="admin@example.com",
                delivery_time="06:45",
                region=DEFAULT_REGION_ID,
                activity="Fish",
                risk="standard",
                density="compact",
            )
            asyncio.run(web_app.api_save_digest_preferences(request, client_id="admin-phone"))

            payload = asyncio.run(web_app.api_update_digest_admin_preference(
                "admin-phone",
                web_app.DigestAdminPreferenceRequest(enabled=False),
            ))
            loaded = asyncio.run(web_app.api_digest_preferences(client_id="admin-phone"))
            audit = asyncio.run(web_app.api_digest_delivery_audit())

            self.assertFalse(payload["preferences"][0]["enabled"])
            self.assertFalse(loaded["preferences"]["enabled"])
            self.assertEqual(audit["audit"][0]["event"], "preference_update")
            self.assertEqual(audit["audit"][0]["reason"], "disabled")

    def test_digest_admin_reports_delivery_health(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            today = datetime.now().date().isoformat()
            web_app.digest_preference_store.save(
                web_app.DigestPreferences(
                    enabled=True,
                    email="admin@example.com",
                    delivery_time="06:45",
                    region=DEFAULT_REGION_ID,
                    activity="Fish",
                    risk="standard",
                    density="compact",
                ),
                "admin-phone",
            )
            for event in (
                {"event": "delivery", "client_id": "admin-phone", "delivered": True, "mode": "outbox", "reason": "queued", "date": today, "recipient": "admin@example.com", "run_id": "run-1"},
                {"event": "delivery", "client_id": "admin-phone", "delivered": False, "mode": "skipped", "reason": "already delivered", "date": today, "recipient": "admin@example.com", "run_id": "run-2"},
                {"event": "delivery", "client_id": "admin-phone", "delivered": False, "mode": "error", "reason": "smtp failed", "date": today, "recipient": "admin@example.com", "run_id": "run-3"},
            ):
                web_app.digest_preference_store.append_audit(event)

            payload = asyncio.run(web_app.api_digest_admin())

            self.assertEqual(payload["health"]["enabled_preferences"], 1)
            self.assertEqual(payload["health"]["today_delivered"], 1)
            self.assertEqual(payload["health"]["today_skipped"], 1)
            self.assertEqual(payload["health"]["today_errors"], 1)
            self.assertEqual(payload["health"]["last_run_id"], "run-3")
            self.assertEqual(payload["health"]["last_error"], "smtp failed")

    def test_run_digest_deliveries_only_sends_due_preferences(self):
        self._use_cache(lambda: StubClient(live_telemetry(), tomorrow_forecast()))
        with tempfile.TemporaryDirectory() as temp_dir:
            web_app.digest_preference_store = DigestPreferenceStore(Path(temp_dir) / "preferences.json")
            web_app.digest_email_sender = DigestEmailSender(Path(temp_dir) / "outbox.json", smtp_enabled=False)
            request = web_app.DigestPreferenceRequest(
                enabled=True,
                email="test@example.com",
                delivery_time="06:00",
                region=DEFAULT_REGION_ID,
                activity="Kayak",
                risk="standard",
                density="full",
            )
            asyncio.run(web_app.api_save_digest_preferences(request, client_id="phone"))

            payload = asyncio.run(web_app.api_run_digest_deliveries(now="2026-06-13T06:01:00", run_id="web-run"))
            repeat = asyncio.run(web_app.api_run_digest_deliveries(now="2026-06-13T07:01:00"))

            self.assertEqual(payload["run_id"], "web-run")
            self.assertTrue(payload["results"][0]["delivered"])
            self.assertEqual(repeat["results"][0]["reason"], "already delivered")
            audit = asyncio.run(web_app.api_digest_delivery_audit(limit=5))
            self.assertEqual(audit["audit"][0]["run_id"], "web-run")

    def test_api_state_applies_risk_tolerance(self):
        telemetry = live_telemetry()
        telemetry["wind_knots"] = 18.0
        self._use_cache(lambda: StubClient(telemetry, live_forecast()))

        standard = asyncio.run(web_app.api_state(region=DEFAULT_REGION_ID, limit=10, risk="standard"))
        conservative = asyncio.run(web_app.api_state(region=DEFAULT_REGION_ID, limit=10, risk="conservative"))

        standard_harbor = next(zone for zone in standard["zones"] if zone["id"] == "gig_harbor")
        conservative_harbor = next(zone for zone in conservative["zones"] if zone["id"] == "gig_harbor")
        self.assertEqual(standard["config"]["risk_tolerance"]["id"], "standard")
        self.assertEqual(conservative["config"]["risk_tolerance"]["id"], "conservative")
        self.assertEqual(standard_harbor["kayak"]["status"], "SAFE")
        self.assertEqual(conservative_harbor["kayak"]["status"], "CAUTION")

    def test_api_state_uses_region_scoped_cache_and_provider_context(self):
        cache = self._use_cache(lambda: StubClient(live_telemetry(), live_forecast()))
        web_app.region_state_caches["port_orchard"] = cache

        payload = asyncio.run(web_app.api_state(region="port_orchard", limit=10))

        self.assertEqual(payload["config"]["region"]["id"], "port_orchard")
        self.assertEqual(payload["config"]["region"]["provider_context"]["tide_station"], BREMERTON_TIDE_STATION)
        self.assertEqual(payload["config"]["region"]["provider_context"]["current_station"], "PUG1514")
        self.assertEqual(payload["config"]["region"]["provider_context"]["current_bin"], 8)
        self.assertEqual(payload["config"]["region"]["provider_context"]["current_station_type"], "H")
        self.assertEqual(payload["config"]["region"]["provider_context"]["provider_confidence"]["level"], "High")
        self.assertEqual(payload["config"]["region"]["provider_context"]["provider_confidence"]["label"], "High station fit")
        self.assertEqual(payload["config"]["region"]["provider_context"]["provider_strategy"]["profile"], "station_backed")
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
        providers = {item["id"]: item for item in payload["providers"]["regions"]}
        self.assertEqual(providers["port_orchard"]["tide_station"], BREMERTON_TIDE_STATION)
        self.assertEqual(providers["port_orchard"]["current_station"], "PUG1514")
        self.assertEqual(providers["port_orchard"]["current_bin"], 8)
        self.assertEqual(providers["port_orchard"]["current_station_type"], "H")
        self.assertEqual(providers["port_orchard"]["provider_confidence"], "High")
        self.assertEqual(providers["tacoma_narrows"]["tide_station"], "9446484")
        self.assertEqual(providers["tacoma_narrows"]["current_station"], "PUG1527")
        self.assertEqual(providers["tacoma_narrows"]["current_bin"], 19)
        self.assertEqual(providers["tacoma_narrows"]["current_bin_depth_ft"], 23)
        self.assertEqual(providers["case_inlet"]["provider_confidence"], "Medium")
        self.assertEqual(providers["south_hood_canal"]["tide_station"], "9445478")
        self.assertEqual(providers["south_hood_canal"]["current_station"], "PUG1601")
        self.assertEqual(providers["south_hood_canal"]["current_bin"], 21)
        self.assertEqual(providers["south_hood_canal"]["provider_confidence"], "Medium")
        self.assertEqual(providers["south_hood_canal"]["provider_confidence_label"], "Sparse current coverage")
        self.assertEqual(providers["south_hood_canal"]["provider_profile"], "sparse_current")
        self.assertTrue(providers["south_hood_canal"]["provider_warnings"])
        self.assertEqual(providers["aberdeen"]["tide_station"], "9441187")
        self.assertEqual(providers["aberdeen"]["current_station"], "ACT8496")
        self.assertEqual(providers["aberdeen"]["current_bin"], 1)
        self.assertEqual(providers["aberdeen"]["provider_confidence"], "Medium")
        self.assertEqual(providers["aberdeen"]["provider_confidence_label"], "River/bar influenced")
        self.assertEqual(providers["aberdeen"]["provider_profile"], "river_bar_influenced")
        self.assertTrue(providers["aberdeen"]["provider_warnings"])


if __name__ == "__main__":
    unittest.main()
