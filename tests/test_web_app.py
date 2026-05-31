import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import web_app
from marine_config import ALL_ZONES, OPTIONAL_ZONES, ZONES


class FakeClient:
    async def fetch_telemetry(self):
        return {
            "current_knots": 1.1,
            "tide_feet": 5.2,
            "wind_knots": 4.0,
            "sources": {
                "current": "test",
                "tide": "test",
                "wind": "test",
            },
            "fallback_reason": None,
        }

    async def fetch_forecast(self):
        start = datetime(2026, 5, 30, 10)
        predictions = [
            {"time": start + timedelta(hours=hour), "tide_feet": 4.0 + hour * 0.3}
            for hour in range(8)
        ]
        return {
            "predictions": predictions,
            "wind_predictions": [
                {"time": point["time"], "wind_knots": 4.0}
                for point in predictions
            ],
            "sources": {
                "tide": "test",
                "current": "derived",
                "wind": "test",
            },
            "fallback_reason": None,
            "wind_fallback_reason": None,
        }


class WebAppTests(unittest.TestCase):
    def test_api_state_returns_json_ready_dashboard_payload(self):
        with patch.object(web_app, "NoaaMarineClient", return_value=FakeClient()):
            payload = asyncio.run(web_app.api_state())

        self.assertEqual(len(payload["zones"]), len(ALL_ZONES))
        self.assertEqual(
            sum(1 for zone in payload["zones"] if zone["active_by_default"]),
            len(ZONES),
        )
        self.assertEqual(
            sum(1 for zone in payload["zones"] if not zone["active_by_default"]),
            len(OPTIONAL_ZONES),
        )
        self.assertEqual(payload["config"]["app"], "TideWindow")
        self.assertEqual(payload["config"]["forecast_hours"], 24)
        self.assertIn("generated_at", payload)
        self.assertIn("confidence", payload)
        self.assertGreater(len(payload["windows"]), 0)
        self.assertGreater(len(payload["timeline"]), 0)
        self.assertIsInstance(payload["windows"][0]["start"], str)
        self.assertIsInstance(payload["timeline"][0]["start"], str)
        self.assertIn("map", payload["zones"][0])
        self.assertIsInstance(payload["forecast"]["predictions"][0]["time"], str)
        self.assertIsInstance(payload["forecast"]["wind_predictions"][0]["time"], str)

    def test_health_returns_lightweight_status_payload(self):
        payload = asyncio.run(web_app.health())

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["app"], "TideWindow")
        self.assertEqual(payload["zones"], len(ALL_ZONES))
        self.assertEqual(payload["default_zones"], len(ZONES))
        self.assertEqual(payload["optional_zones"], len(OPTIONAL_ZONES))
        self.assertIn("generated_at", payload)
        self.assertIn("providers", payload)
        self.assertIn("noaa_tide_station", payload["providers"])


if __name__ == "__main__":
    unittest.main()
