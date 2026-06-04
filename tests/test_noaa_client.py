import unittest
from datetime import datetime, timedelta

from marine_config import (
    SEEDED_CURRENT_DIRECTION,
    SEEDED_CURRENT_KNOTS,
    SEEDED_TIDE_FEET,
)
from noaa_client import NoaaMarineClient


class NoaaMarineClientForecastTests(unittest.TestCase):
    def test_parse_forecast_payload_filters_and_shapes_predictions(self):
        client = NoaaMarineClient()
        start = datetime(2026, 5, 30, 8, 30)
        end = start + timedelta(hours=3)
        payload = {
            "predictions": [
                {"t": "2026-05-30 08:00", "v": "1.0"},
                {"t": "2026-05-30 09:00", "v": "2.0"},
                {"t": "2026-05-30 10:00", "v": "3.5"},
                {"t": "2026-05-30 11:00", "v": "4.0"},
                {"t": "2026-05-30 12:00", "v": "5.0"},
            ]
        }

        forecast = client._parse_forecast_payload(payload, start, end)

        self.assertEqual(
            forecast["sources"],
            {"tide": "live", "current": "derived", "wind": "fallback"},
        )
        self.assertEqual(forecast["wind_predictions"], [])
        self.assertIsNone(forecast["fallback_reason"])
        self.assertEqual(len(forecast["predictions"]), 3)
        self.assertEqual(forecast["predictions"][0]["time"], datetime(2026, 5, 30, 9))
        self.assertEqual(forecast["predictions"][0]["tide_feet"], 2.0)

    def test_parse_forecast_payload_falls_back_with_too_few_points(self):
        client = NoaaMarineClient()
        start = datetime(2026, 5, 30, 8)
        end = start + timedelta(hours=3)

        forecast = client._parse_forecast_payload(
            {"predictions": [{"t": "2026-05-30 09:00", "v": "2.0"}]},
            start,
            end,
        )

        self.assertEqual(
            forecast["sources"],
            {"tide": "seed", "current": "derived", "wind": "fallback"},
        )
        self.assertEqual(
            forecast["fallback_reason"],
            "NOAA returned too few tide predictions",
        )

    def test_parse_wind_forecast_payload_converts_hourly_mph_to_knots(self):
        client = NoaaMarineClient()
        client.owm_api_key = "test-key"
        start = datetime(2026, 5, 30, 8)
        end = start + timedelta(hours=2)
        payload = {
            "hourly": [
                {"dt": int(datetime(2026, 5, 30, 8).timestamp()), "wind_speed": 10.0},
                {"dt": int(datetime(2026, 5, 30, 9).timestamp()), "wind_speed": 12.0},
                {"dt": int(datetime(2026, 5, 30, 12).timestamp()), "wind_speed": 20.0},
            ]
        }

        wind = client._parse_wind_forecast_payload(payload, start, end)

        self.assertEqual(wind["source"], "live")
        self.assertIsNone(wind["fallback_reason"])
        self.assertEqual(len(wind["predictions"]), 2)
        self.assertAlmostEqual(wind["predictions"][0]["wind_knots"], 8.68976)

    def test_parse_wind_forecast_payload_marks_missing_hourly_data(self):
        client = NoaaMarineClient()
        client.owm_api_key = "test-key"
        start = datetime(2026, 5, 30, 8)
        end = start + timedelta(hours=2)

        wind = client._parse_wind_forecast_payload(
            {"cod": 401, "message": "Invalid API key"},
            start,
            end,
        )

        self.assertEqual(wind["source"], "missing")
        self.assertEqual(wind["fallback_reason"], "Invalid API key")


class NoaaMarineClientTelemetryTests(unittest.TestCase):
    def test_live_tide_with_predicted_current_does_not_seed_tide(self):
        client = NoaaMarineClient()
        result = client._parse_payload(
            tide_json={"data": [{"v": "6.2"}]},
            current_json={"data": []},
            live_wind=5.0,
            current_predictions=[{"time": datetime.now(), "speed": 1.3, "dir": 150.0}],
        )

        self.assertEqual(
            result["sources"],
            {"tide": "live", "current": "predicted", "wind": "live"},
        )
        self.assertIsNone(result["fallback_reason"])
        self.assertEqual(result["tide_feet"], 6.2)
        self.assertEqual(result["current_knots"], 1.3)
        self.assertEqual(result["current_direction"], 150.0)

    def test_missing_tide_and_current_degrade_independently_to_seed(self):
        client = NoaaMarineClient()
        result = client._parse_payload(
            tide_json={"data": []},
            current_json={"data": []},
            live_wind=None,
            current_predictions=[],
        )

        self.assertEqual(
            result["sources"],
            {"tide": "seed", "current": "seed", "wind": "fallback"},
        )
        self.assertEqual(result["tide_feet"], SEEDED_TIDE_FEET)
        self.assertEqual(result["current_knots"], SEEDED_CURRENT_KNOTS)
        self.assertIn("tide", result["fallback_reason"])
        self.assertIn("current", result["fallback_reason"])

    def test_live_current_is_preferred_over_predictions(self):
        client = NoaaMarineClient()
        result = client._parse_payload(
            tide_json={"data": [{"v": "6.0"}]},
            current_json={"data": [{"s": "0.9", "d": "150"}]},
            live_wind=4.0,
            current_predictions=[{"time": datetime.now(), "speed": 9.9, "dir": 10.0}],
        )

        self.assertEqual(result["sources"]["current"], "live")
        self.assertEqual(result["current_knots"], 0.9)

    def test_parse_current_predictions_normalizes_and_skips_bad_points(self):
        payload = {
            "current_predictions": {
                "cp": [
                    {"Time": "2026-06-03 14:30", "Speed": "1.5", "Direction": "140"},
                    {"Time": "not-a-time", "Speed": "1.0"},
                    {"Speed": "1.0"},
                    {"Time": "2026-06-03 15:00", "Velocity_Major": "-0.8"},
                ]
            }
        }

        parsed = NoaaMarineClient._parse_current_predictions(payload)

        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["time"], datetime(2026, 6, 3, 14, 30))
        self.assertEqual(parsed[0]["speed"], 1.5)
        self.assertEqual(parsed[0]["dir"], 140.0)
        # Velocity_Major is taken as magnitude; direction defaults when absent.
        self.assertEqual(parsed[1]["speed"], 0.8)
        self.assertEqual(parsed[1]["dir"], SEEDED_CURRENT_DIRECTION)

    def test_parse_current_predictions_handles_empty_payload(self):
        self.assertEqual(NoaaMarineClient._parse_current_predictions(None), [])
        self.assertEqual(NoaaMarineClient._parse_current_predictions({}), [])


if __name__ == "__main__":
    unittest.main()
