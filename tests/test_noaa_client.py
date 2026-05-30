import unittest
from datetime import datetime, timedelta

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


if __name__ == "__main__":
    unittest.main()
