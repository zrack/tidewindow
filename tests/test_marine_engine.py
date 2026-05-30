import unittest

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


if __name__ == "__main__":
    unittest.main()
