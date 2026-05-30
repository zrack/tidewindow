import unittest
from datetime import datetime

from marine_config import VISIBLE_ZONE_COUNT, ZONES
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
                "wind_source": "live",
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
                "wind_source": "fallback",
            },
        ]
        self.forecast = {
            "sources": {"tide": "live", "current": "derived", "wind": "live"},
            "fallback_reason": None,
            "wind_fallback_reason": None,
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
        self.assertIn("Wind: live", output)
        self.assertIn("Kayak", output)
        self.assertIn("Fish", output)

    def test_forecast_formatter_keeps_diagnostics_compact_by_default(self):
        self.forecast["wind_fallback_reason"] = "Very long provider error message"

        output = self.app._format_forecast(
            self.windows,
            self.forecast,
            self.confidence,
        )

        self.assertIn("Hourly wind unavailable; using current wind.", output)
        self.assertIn("Press d for details.", output)
        self.assertNotIn("Very long provider error message", output)

    def test_forecast_formatter_shows_diagnostics_when_enabled(self):
        self.app.show_diagnostics = True
        self.forecast["wind_fallback_reason"] = "Very long provider error message"

        output = self.app._format_forecast(
            self.windows,
            self.forecast,
            self.confidence,
        )

        self.assertIn("Very long provider error message", output)

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

    def test_source_status_uses_compact_notice(self):
        output = self.app._format_source_status(
            {
                "updated_at": "2026-05-30 15:29:57",
                "sources": {"tide": "seed", "current": "seed", "wind": "fallback"},
                "fallback_reason": "NOAA returned an empty tide or current payload",
            }
        )

        self.assertIn("live NOAA telemetry unavailable", output)
        self.assertNotIn("empty tide", output)

    def test_zone_pages_show_three_areas_at_a_time(self):
        first_page = self.app._visible_zone_ids()

        self.app.zone_page = 1
        second_page = self.app._visible_zone_ids()

        self.assertEqual(len(first_page), VISIBLE_ZONE_COUNT)
        self.assertEqual(first_page, list(ZONES.keys())[:VISIBLE_ZONE_COUNT])
        self.assertEqual(second_page, list(ZONES.keys())[VISIBLE_ZONE_COUNT:VISIBLE_ZONE_COUNT * 2])
        self.assertEqual(self.app._zone_page_count(), 3)


if __name__ == "__main__":
    unittest.main()
