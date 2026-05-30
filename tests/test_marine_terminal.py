import unittest
from datetime import datetime

from marine_terminal import MarineTerminalApp


class MarineTerminalForecastFormatTests(unittest.TestCase):
    def setUp(self):
        self.app = MarineTerminalApp()
        self.windows = [
            {
                "activity": "Kayak",
                "zone_title": "INSIDE GIG HARBOR",
                "start": datetime(2026, 5, 30, 15),
                "end": datetime(2026, 5, 30, 16),
                "status": "SAFE",
                "phase": "Flood/Rising",
                "current": 0.1,
                "wind": 4.0,
            },
            {
                "activity": "Fish",
                "zone_title": "PURDY BRIDGE (HENDERSON BAY)",
                "start": datetime(2026, 5, 30, 21),
                "end": datetime(2026, 5, 30, 22),
                "status": "OPTIMAL",
                "phase": "Ebb/Falling",
                "current": 2.1,
                "wind": 6.0,
            },
        ]
        self.forecast = {
            "sources": {"tide": "live", "current": "derived"},
            "fallback_reason": None,
        }
        self.confidence = {
            "level": "Medium",
            "color": "yellow",
            "note": "Live tide forecast with derived current guidance.",
        }

    def test_forecast_formatter_includes_confidence(self):
        output = self.app._format_forecast(
            self.windows,
            self.forecast,
            self.confidence,
        )

        self.assertIn("Confidence:", output)
        self.assertIn("Medium", output)
        self.assertIn("Kayak", output)
        self.assertIn("Fish", output)

    def test_forecast_filter_can_show_kayak_only(self):
        self.app.forecast_filter = "Kayak"

        output = self.app._format_forecast(
            self.windows,
            self.forecast,
            self.confidence,
        )

        self.assertIn("Mode: Kayak", output)
        self.assertIn("Kayak", output)
        self.assertNotIn("Fish Sat", output)


if __name__ == "__main__":
    unittest.main()
