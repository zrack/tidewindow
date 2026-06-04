import unittest

from marine_config import ALL_ZONES, NOAA_CURRENT_STATION, NOAA_TIDE_STATION, OPTIONAL_ZONES, ZONES
from marine_regions import (
    BREMERTON_TIDE_STATION,
    DEFAULT_REGION_ID,
    REGIONS,
    SPOTS,
    default_spot_ids_for_region,
    gig_harbor_parity_snapshot,
    get_region,
    optional_spot_ids_for_region,
    provider_context_for_region,
    ranked_spots_for_region,
    region_summaries,
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
        self.assertTrue(set(ALL_ZONES).issubset(SPOTS))

    def test_default_and_optional_spots_match_legacy_sets(self):
        self.assertEqual(default_spot_ids_for_region(DEFAULT_REGION_ID), tuple(ZONES.keys()))
        self.assertEqual(optional_spot_ids_for_region(DEFAULT_REGION_ID), tuple(OPTIONAL_ZONES.keys()))

    def test_visible_spots_returns_top_ranked_region_spots(self):
        ranked = ranked_spots_for_region(DEFAULT_REGION_ID)
        visible = visible_spots_for_region(DEFAULT_REGION_ID, limit=10)

        self.assertEqual(len(visible), 10)
        self.assertEqual([spot["id"] for spot in visible], [spot["id"] for spot in ranked[:10]])
        self.assertTrue(all(DEFAULT_REGION_ID in spot["region_ids"] for spot in visible))

    def test_visible_spots_clamps_to_region_size(self):
        visible = visible_spots_for_region(DEFAULT_REGION_ID, limit=999)

        self.assertEqual(len(visible), len(ALL_ZONES))

    def test_region_summaries_are_public_control_metadata(self):
        summaries = region_summaries()
        gig_harbor = summaries[0]

        self.assertEqual(gig_harbor["id"], DEFAULT_REGION_ID)
        self.assertEqual(gig_harbor["name"], "Gig Harbor")
        self.assertEqual(gig_harbor["default_spot_limit"], 10)
        self.assertEqual(gig_harbor["spot_count"], len(ALL_ZONES))
        self.assertNotIn("provider_context", gig_harbor)

    def test_requested_city_regions_are_selectable(self):
        requested = {
            "port_orchard": "Port Orchard",
            "bremerton": "Bremerton",
            "silverdale": "Silverdale",
            "tacoma_narrows": "Tacoma Narrows",
            "carr_inlet": "Carr Inlet",
            "case_inlet": "Case Inlet",
            "anderson_island": "Anderson Island",
            "steilacoom_nisqually": "Steilacoom & Nisqually",
            "olympia_budd_inlet": "Olympia & Budd Inlet",
            "south_hood_canal": "South Hood Canal",
            "aberdeen": "Aberdeen",
        }

        summaries = {region["id"]: region for region in region_summaries()}

        for region_id, name in requested.items():
            with self.subTest(region=region_id):
                region = get_region(region_id)
                self.assertEqual(region["name"], name)
                self.assertIn(region["type"], {"city", "subregion"})
                self.assertGreaterEqual(len(region["spot_ids"]), 10)
                self.assertEqual(summaries[region_id]["spot_count"], len(region["spot_ids"]))
                self.assertEqual(len(visible_spots_for_region(region_id, limit=10)), 10)

    def test_regions_carry_station_and_current_bin_context(self):
        expected = {
            "port_orchard": (BREMERTON_TIDE_STATION, "PUG1514", 8),
            "bremerton": (BREMERTON_TIDE_STATION, "PUG1510", 6),
            "silverdale": (BREMERTON_TIDE_STATION, "PUG1510", 6),
            "tacoma_narrows": ("9446484", "PUG1527", 19),
            "carr_inlet": ("9446291", "PUG1530", 18),
            "case_inlet": ("9446281", "PUG1548", 10),
            "anderson_island": ("9446804", "PUG1535", 16),
            "steilacoom_nisqually": ("9446714", "PUG1532", 16),
            "olympia_budd_inlet": ("9446807", "PUG1540", 10),
            "south_hood_canal": ("9445478", "PUG1601", 21),
            "aberdeen": ("9441187", "ACT8496", 1),
        }

        for region_id, (tide_station, current_station, current_bin) in expected.items():
            with self.subTest(region=region_id):
                context = provider_context_for_region(region_id)
                self.assertEqual(context["tide_station"], tide_station)
                self.assertEqual(context["current_station"], current_station)
                self.assertEqual(context["current_bin"], current_bin)
                self.assertIn("current_bin_depth_ft", context)
                self.assertIn(context["current_station_type"], {"H", "S", "W"})
                self.assertIn(context["tide_station_type"], {"R", "S"})
                self.assertIn(context["provider_confidence"]["level"], {"High", "Medium", "Low"})
                self.assertIn("weather_lat", context)
                self.assertIn("weather_lon", context)

    def test_provider_confidence_downgrades_subordinate_tide_context(self):
        context = provider_context_for_region("case_inlet")

        self.assertEqual(context["tide_station_type"], "S")
        self.assertEqual(context["current_station_type"], "H")
        self.assertEqual(context["provider_confidence"]["level"], "Medium")

    def test_aberdeen_uses_coastal_provider_context(self):
        context = provider_context_for_region("aberdeen")

        self.assertEqual(context["nws_zone"], "PZZ110")
        self.assertEqual(context["tide_station_name"], "Aberdeen")
        self.assertEqual(context["current_station_name"], "Grays Harbor Entrance")
        self.assertEqual(context["current_station_type"], "S")
        self.assertEqual(context["provider_confidence"]["level"], "Medium")

    def test_places_without_station_context_are_not_selectable_regions(self):
        for region_id in ("chico", "gorst"):
            with self.subTest(region=region_id):
                with self.assertRaisesRegex(ValueError, "Unknown TideWindow region"):
                    get_region(region_id)

    def test_parity_snapshot_documents_current_contract(self):
        snapshot = gig_harbor_parity_snapshot()

        self.assertEqual(snapshot["zone_ids"], snapshot["legacy_zone_ids"])
        self.assertEqual(snapshot["default_ids"], snapshot["legacy_default_ids"])
        self.assertEqual(snapshot["optional_ids"], snapshot["legacy_optional_ids"])

    def test_unknown_region_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown TideWindow region"):
            get_region("not_a_region")


if __name__ == "__main__":
    unittest.main()
