import unittest
from datetime import date

from sun_times import sun_events

# Gig Harbor / Tacoma Narrows.
LAT = 47.2690
LON = -122.5517


class SunTimesTests(unittest.TestCase):
    def test_event_ordering_on_a_normal_day(self):
        events = sun_events(LAT, LON, date(2026, 6, 3))
        for key in ("sunrise", "sunset", "dawn", "dusk"):
            self.assertIsNotNone(events[key], key)
        # Civil dawn < sunrise < sunset < civil dusk.
        self.assertLess(events["dawn"], events["sunrise"])
        self.assertLess(events["sunrise"], events["sunset"])
        self.assertLess(events["sunset"], events["dusk"])

    def test_summer_has_more_daylight_than_winter(self):
        summer = sun_events(LAT, LON, date(2026, 6, 21))
        winter = sun_events(LAT, LON, date(2026, 12, 21))
        summer_seconds = (summer["sunset"] - summer["sunrise"]).total_seconds()
        winter_seconds = (winter["sunset"] - winter["sunrise"]).total_seconds()
        self.assertGreater(summer_seconds, winter_seconds)
        # Sanity: Gig Harbor summer days run ~15-16 hours.
        self.assertGreater(summer_seconds, 14 * 3600)
        self.assertLess(summer_seconds, 17 * 3600)

    def test_polar_night_has_no_sunrise(self):
        # Svalbard in deep winter: the sun never rises.
        events = sun_events(78.0, 15.0, date(2026, 12, 21))
        self.assertIsNone(events["sunrise"])
        self.assertIsNone(events["sunset"])


if __name__ == "__main__":
    unittest.main()
