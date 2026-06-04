import unittest
from datetime import datetime, timedelta

from marine_config import ZONES
from marine_engine import MarineSafetyEngine


class MarineSafetyEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = MarineSafetyEngine()

    def test_zone_telemetry_uses_configured_multipliers(self):
        zones = self.engine.get_zone_telemetry(
            base_current=2.0,
            base_tide=7.5,
            base_wind=10.0,
        )

        self.assertAlmostEqual(zones["purdy_bridge"]["current"], 2.8)
        self.assertAlmostEqual(zones["purdy_bridge"]["wind"], 8.0)
        self.assertAlmostEqual(zones["gig_harbor"]["current"], 0.1)
        self.assertAlmostEqual(zones["gig_harbor"]["wind"], 6.0)
        self.assertAlmostEqual(zones["fox_island"]["current"], 1.3)
        self.assertAlmostEqual(zones["fox_island"]["wind"], 12.0)
        self.assertAlmostEqual(zones["fox_island"]["tide"], 7.5)
        self.assertAlmostEqual(zones["sunrise_beach"]["current"], 1.5)
        self.assertAlmostEqual(zones["narrows_park"]["current"], 2.3)
        self.assertAlmostEqual(zones["fox_island_pier"]["wind"], 12.5)
        self.assertAlmostEqual(zones["purdy_sand_spit"]["current"], 2.5)
        self.assertAlmostEqual(zones["kopachuck"]["wind"], 9.5)
        self.assertEqual(len(zones), len(ZONES))

    def test_purdy_kayaking_marks_fast_current_dangerous(self):
        result = self.engine.evaluate_kayaking(
            zone="purdy_bridge",
            current=2.1,
            wind=4.0,
        )

        self.assertEqual(result["status"], "DANGER")
        self.assertEqual(result["color"], "red")

    def test_gig_harbor_kayaking_is_wind_driven(self):
        safe = self.engine.evaluate_kayaking(
            zone="gig_harbor",
            current=0.1,
            wind=10.0,
        )
        caution = self.engine.evaluate_kayaking(
            zone="gig_harbor",
            current=0.1,
            wind=16.0,
        )

        self.assertEqual(safe["status"], "SAFE")
        self.assertEqual(caution["status"], "CAUTION")

    def test_fox_island_kayaking_treats_exposure_as_risk(self):
        caution = self.engine.evaluate_kayaking(
            zone="fox_island",
            current=1.1,
            wind=6.0,
        )
        danger = self.engine.evaluate_kayaking(
            zone="fox_island",
            current=0.5,
            wind=12.1,
        )

        self.assertEqual(caution["status"], "CAUTION")
        self.assertEqual(danger["status"], "DANGER")

    def test_new_beach_zones_have_named_safety_thresholds(self):
        narrows = self.engine.evaluate_kayaking(
            zone="narrows_park",
            current=1.9,
            wind=5.0,
        )
        kopachuck = self.engine.evaluate_fly_fishing(
            zone="kopachuck",
            current=0.5,
            tide=8.4,
        )

        self.assertEqual(narrows["status"], "DANGER")
        self.assertEqual(kopachuck["status"], "OPTIMAL")

    def test_fly_fishing_thresholds(self):
        purdy_optimal = self.engine.evaluate_fly_fishing(
            zone="purdy_bridge",
            current=1.2,
            tide=5.0,
        )
        harbor_optimal = self.engine.evaluate_fly_fishing(
            zone="gig_harbor",
            current=0.1,
            tide=8.1,
        )
        fox_wait = self.engine.evaluate_fly_fishing(
            zone="fox_island",
            current=0.2,
            tide=6.0,
        )

        self.assertEqual(purdy_optimal["status"], "OPTIMAL")
        self.assertEqual(harbor_optimal["status"], "OPTIMAL")
        self.assertEqual(fox_wait["status"], "CAUTION")

    def test_unknown_configured_zone_gets_generic_thresholds(self):
        kayak = self.engine.evaluate_kayaking(
            zone="new_zone",
            current=0.4,
            wind=4.0,
        )
        fish = self.engine.evaluate_fly_fishing(
            zone="new_zone",
            current=1.0,
            tide=6.0,
        )

        self.assertEqual(kayak["status"], "SAFE")
        self.assertEqual(fish["status"], "OPTIMAL")

    def test_forecast_windows_include_kayak_and_fish_recommendations(self):
        start = datetime(2026, 5, 30, 6)
        tide_predictions = [
            {"time": start, "tide_feet": 2.0},
            {"time": start + timedelta(hours=1), "tide_feet": 2.2},
            {"time": start + timedelta(hours=2), "tide_feet": 3.8},
            {"time": start + timedelta(hours=3), "tide_feet": 5.4},
            {"time": start + timedelta(hours=4), "tide_feet": 5.5},
        ]

        windows = self.engine.build_forecast_windows(
            tide_predictions=tide_predictions,
            wind_knots=5.0,
            max_windows_per_activity=2,
        )
        activities = [window["activity"] for window in windows]

        self.assertEqual(activities.count("Kayak"), 2)
        self.assertEqual(activities.count("Fish"), 2)
        self.assertTrue(all(window["start"] < window["end"] for window in windows))

    def test_forecast_phase_marks_low_current_as_slackish(self):
        start = datetime(2026, 5, 30, 6)
        tide_predictions = [
            {"time": start, "tide_feet": 4.0},
            {"time": start + timedelta(hours=1), "tide_feet": 4.1},
        ]

        windows = self.engine.build_forecast_windows(
            tide_predictions=tide_predictions,
            wind_knots=4.0,
            max_windows_per_activity=1,
        )

        self.assertTrue(all(window["phase"] == "Slack-ish" for window in windows))

    def test_forecast_windows_use_hourly_wind_when_available(self):
        start = datetime(2026, 5, 30, 6)
        tide_predictions = [
            {"time": start, "tide_feet": 2.0},
            {"time": start + timedelta(hours=1), "tide_feet": 3.0},
            {"time": start + timedelta(hours=2), "tide_feet": 4.0},
        ]
        wind_predictions = [
            {"time": start + timedelta(minutes=30), "wind_knots": 20.0},
            {"time": start + timedelta(hours=1, minutes=30), "wind_knots": 4.0},
        ]

        windows = self.engine.build_forecast_windows(
            tide_predictions=tide_predictions,
            wind_knots=6.0,
            wind_predictions=wind_predictions,
            wind_source="live",
            max_windows_per_activity=1,
        )

        self.assertTrue(all(window["wind_source"] == "live" for window in windows))
        self.assertTrue(any(window["wind"] != 6.0 for window in windows))

    def test_forecast_windows_prefer_noaa_current_predictions(self):
        start = datetime(2026, 5, 30, 6)
        tide_predictions = [
            {"time": start, "tide_feet": 2.0},
            {"time": start + timedelta(hours=1), "tide_feet": 2.1},
            {"time": start + timedelta(hours=2), "tide_feet": 2.2},
        ]
        current_predictions = [
            {"time": start + timedelta(minutes=30), "speed": 1.4, "dir": 150.0},
            {"time": start + timedelta(hours=1, minutes=30), "speed": 1.6, "dir": 20.0},
        ]

        windows = self.engine.build_forecast_windows(
            tide_predictions=tide_predictions,
            wind_knots=4.0,
            current_predictions=current_predictions,
            current_source="predicted",
            max_windows_per_activity=1,
        )

        self.assertTrue(all(window["current_source"] == "predicted" for window in windows))
        self.assertTrue(any(window["current"] > 1.0 for window in windows))
        self.assertTrue(any(window["phase"] in {"Flood/South", "Ebb/North"} for window in windows))

    def test_hourly_timeline_includes_zone_scores(self):
        start = datetime(2026, 5, 30, 6)
        tide_predictions = [
            {"time": start, "tide_feet": 2.0},
            {"time": start + timedelta(hours=1), "tide_feet": 3.0},
            {"time": start + timedelta(hours=2), "tide_feet": 4.0},
        ]

        timeline = self.engine.build_hourly_timeline(
            tide_predictions=tide_predictions,
            wind_knots=5.0,
        )

        self.assertEqual(len(timeline), 2)
        self.assertIn("purdy_bridge", timeline[0]["zones"])
        self.assertEqual(timeline[0]["current_source"], "derived")
        self.assertIn("kayak_score", timeline[0]["zones"]["purdy_bridge"])
        self.assertIn("fish_score", timeline[0]["zones"]["purdy_bridge"])

    def test_confidence_is_high_for_all_live_light_wind(self):
        telemetry = {
            "sources": {"tide": "live", "current": "live", "wind": "live"},
            "fallback_reason": None,
        }
        forecast = {
            "sources": {"tide": "live", "current": "live", "wind": "live"},
            "fallback_reason": None,
        }

        confidence = self.engine.evaluate_confidence(
            telemetry=telemetry,
            forecast=forecast,
            wind_knots=6.0,
        )

        self.assertEqual(confidence["level"], "High")

    def test_confidence_is_medium_for_live_tide_and_derived_current(self):
        telemetry = {
            "sources": {"tide": "live", "current": "live", "wind": "fallback"},
            "fallback_reason": None,
        }
        forecast = {
            "sources": {"tide": "live", "current": "derived", "wind": "live"},
            "fallback_reason": None,
        }

        confidence = self.engine.evaluate_confidence(
            telemetry=telemetry,
            forecast=forecast,
            wind_knots=8.0,
        )

        self.assertEqual(confidence["level"], "Medium")

    def test_confidence_is_low_when_seed_data_is_used(self):
        telemetry = {
            "sources": {"tide": "seed", "current": "seed", "wind": "seed"},
            "fallback_reason": "NOAA unavailable",
        }
        forecast = {
            "sources": {"tide": "seed", "current": "derived", "wind": "fallback"},
            "fallback_reason": "forecast unavailable",
        }

        confidence = self.engine.evaluate_confidence(
            telemetry=telemetry,
            forecast=forecast,
            wind_knots=6.0,
        )

        self.assertEqual(confidence["level"], "Low")

    def test_confidence_is_low_when_forecast_wind_is_missing(self):
        telemetry = {
            "sources": {"tide": "live", "current": "live", "wind": "live"},
            "fallback_reason": None,
        }
        forecast = {
            "sources": {"tide": "live", "current": "derived", "wind": "missing"},
            "fallback_reason": None,
        }

        confidence = self.engine.evaluate_confidence(
            telemetry=telemetry,
            forecast=forecast,
            wind_knots=6.0,
        )

        self.assertEqual(confidence["level"], "Low")

    def test_confidence_is_medium_when_showing_last_good_data(self):
        telemetry = {
            "sources": {"tide": "live", "current": "predicted", "wind": "live"},
            "fallback_reason": None,
            "stale": True,
        }
        forecast = {
            "sources": {"tide": "live", "current": "predicted", "wind": "live"},
            "fallback_reason": None,
            "stale": False,
        }

        confidence = self.engine.evaluate_confidence(
            telemetry=telemetry,
            forecast=forecast,
            wind_knots=6.0,
        )

        self.assertEqual(confidence["level"], "Medium")
        self.assertIn("last good", confidence["note"])


if __name__ == "__main__":
    unittest.main()
