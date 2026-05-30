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

        self.assertEqual(forecast["sources"], {"tide": "live", "current": "derived"})
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

        self.assertEqual(forecast["sources"], {"tide": "seed", "current": "derived"})
        self.assertEqual(
            forecast["fallback_reason"],
            "NOAA returned too few tide predictions",
        )


if __name__ == "__main__":
    unittest.main()
