import unittest

from marine_config import ALL_ZONES, NOAA_CURRENT_STATION, NOAA_TIDE_STATION, OPTIONAL_ZONES, ZONES
from marine_regions import (
    DEFAULT_REGION_ID,
    REGIONS,
    SPOTS,
    default_spot_ids_for_region,
    gig_harbor_parity_snapshot,
    get_region,
    optional_spot_ids_for_region,
    ranked_spots_for_region,
    visible_spots_for_region,
    zone_configs_for_region,
)


class MarineRegionTests(unittest.TestCase):
    def test_gig_harbor_region_carries_provider_context(self):
        region = get_region(DEFAULT_REGION_ID)

        self.assertEqual(region["type"], "city")
        self.assertEqual(region["provider_context"]["tide_station"], NOAA_TIDE_STATION)
        self.assertEqual(region["provider_context"]["current_station"], NOAA_CURRENT_STATION)
        self.assertEqual(region["default_spot_limit"], 10)
        self.assertIn(DEFAULT_REGION_ID, REGIONS)

    def test_spot_catalog_preserves_legacy_zone_configs(self):
        zone_configs = zone_configs_for_region(DEFAULT_REGION_ID)

        self.assertEqual(tuple(zone_configs.keys()), tuple(ALL_ZONES.keys()))
        self.assertEqual(zone_configs, ALL_ZONES)
        self.assertEqual(tuple(SPOTS.keys()), tuple(ALL_ZONES.keys()))

    def test_default_and_optional_spots_match_legacy_sets(self):
        self.assertEqual(default_spot_ids_for_region(DEFAULT_REGION_ID), tuple(ZONES.keys()))
        self.assertEqual(optional_spot_ids_for_region(DEFAULT_REGION_ID), tuple(OPTIONAL_ZONES.keys()))

    def test_visible_spots_returns_top_ranked_region_spots(self):
        ranked = ranked_spots_for_region(DEFAULT_REGION_ID)
        visible = visible_spots_for_region(DEFAULT_REGION_ID, limit=10)

        self.assertEqual(len(visible), 10)
        self.assertEqual([spot["id"] for spot in visible], [spot["id"] for spot in ranked[:10]])
        self.assertTrue(all(DEFAULT_REGION_ID in spot["region_ids"] for spot in visible))

    def test_parity_snapshot_documents_current_contract(self):
        snapshot = gig_harbor_parity_snapshot()

        self.assertEqual(snapshot["zone_ids"], snapshot["legacy_zone_ids"])
        self.assertEqual(snapshot["default_ids"], snapshot["legacy_default_ids"])
        self.assertEqual(snapshot["optional_ids"], snapshot["legacy_optional_ids"])

    def test_unknown_region_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown TideWindow region"):
            get_region("port_orchard")


if __name__ == "__main__":
    unittest.main()
