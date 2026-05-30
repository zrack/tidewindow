import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import web_app
from marine_config import ZONES


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

        self.assertEqual(len(payload["zones"]), len(ZONES))
        self.assertIn("generated_at", payload)
        self.assertIn("confidence", payload)
        self.assertGreater(len(payload["windows"]), 0)
        self.assertIsInstance(payload["windows"][0]["start"], str)
        self.assertIsInstance(payload["forecast"]["predictions"][0]["time"], str)
        self.assertIsInstance(payload["forecast"]["wind_predictions"][0]["time"], str)


if __name__ == "__main__":
    unittest.main()
