import unittest

from marine_config import ALL_ZONES, NOAA_CURRENT_STATION, NOAA_TIDE_STATION, OPTIONAL_ZONES, ZONES
from marine_engine import MarineSafetyEngine
from marine_regions import (
    BREMERTON_TIDE_STATION,
    DEFAULT_REGION_ID,
    REVIEWED_SPOT_EXPOSURE_BEARINGS,
    REGIONAL_SPOTS,
    REGIONS,
    SPOTS,
    default_spot_ids_for_region,
    gig_harbor_parity_snapshot,
    get_region,
    optional_spot_ids_for_region,
    provider_context_for_region,
    ranked_spots_for_region,
    region_search_aliases,
    region_summaries,
    resolve_region_query,
    visible_spots_for_region,
    zone_configs_for_region,
)


class MarineRegionTests(unittest.TestCase):
    def test_gig_harbor_region_carries_provider_context(self):
        region = get_region(DEFAULT_REGION_ID)

        self.assertEqual(region["type"], "city")
        self.assertEqual(region["provider_context"]["tide_station"], NOAA_TIDE_STATION)
        self.assertEqual(region["provider_context"]["current_station"], NOAA_CURRENT_STATION)
        self.assertEqual(region["default_spot_limit"], len(ALL_ZONES))
        self.assertIn(DEFAULT_REGION_ID, REGIONS)

    def test_spot_catalog_preserves_legacy_zone_configs(self):
        zone_configs = zone_configs_for_region(DEFAULT_REGION_ID)

        self.assertEqual(tuple(zone_configs.keys()), tuple(ALL_ZONES.keys()))
        self.assertEqual(zone_configs, ALL_ZONES)
        self.assertTrue(set(ALL_ZONES).issubset(SPOTS))

    def test_regional_spots_include_wind_exposure_bearings(self):
        for spot_id, spot in REGIONAL_SPOTS.items():
            with self.subTest(spot=spot_id):
                self.assertIn("wind_exposure_bearing", spot)
                self.assertIn("wind_exposure_basis", spot)
                self.assertGreaterEqual(spot["wind_exposure_bearing"], 0)
                self.assertLess(spot["wind_exposure_bearing"], 360)

    def test_reviewed_spot_exposure_bearings_override_shoreline_family(self):
        for spot_id, bearing in REVIEWED_SPOT_EXPOSURE_BEARINGS.items():
            with self.subTest(spot=spot_id):
                self.assertEqual(REGIONAL_SPOTS[spot_id]["wind_exposure_bearing"], bearing)
                self.assertEqual(REGIONAL_SPOTS[spot_id]["wind_exposure_basis"], "spot_reviewed")

        self.assertEqual(REGIONAL_SPOTS["waterman_pier"]["wind_exposure_basis"], "shoreline_family")

    def test_regional_spots_use_generic_configurable_rule_profiles(self):
        for spot_id, spot in REGIONAL_SPOTS.items():
            with self.subTest(spot=spot_id):
                self.assertEqual(spot["kayak_rule_profile"], "generic")
                self.assertEqual(spot["fish_rule_profile"], "generic")

    def test_regional_zone_configs_preserve_wind_exposure_for_scoring(self):
        zones_config = zone_configs_for_region("south_hood_canal", limit=10)
        spot = zones_config["union_hood_canal"]
        bearing = spot["wind_exposure_bearing"]
        sheltered_bearing = (bearing + 180) % 360
        engine = MarineSafetyEngine()

        exposed = engine.get_zone_telemetry(
            base_current=1.0,
            base_tide=7.0,
            base_wind=10.0,
            base_wind_direction=bearing,
            zones_config={"union_hood_canal": spot},
        )
        sheltered = engine.get_zone_telemetry(
            base_current=1.0,
            base_tide=7.0,
            base_wind=10.0,
            base_wind_direction=sheltered_bearing,
            zones_config={"union_hood_canal": spot},
        )

        self.assertGreater(
            exposed["union_hood_canal"]["wind"],
            sheltered["union_hood_canal"]["wind"],
        )
        self.assertEqual(exposed["union_hood_canal"]["wind_exposure"], "exposed")
        self.assertEqual(sheltered["union_hood_canal"]["wind_exposure"], "sheltered")

    def test_default_and_optional_spots_match_legacy_sets(self):
        self.assertEqual(default_spot_ids_for_region(DEFAULT_REGION_ID), tuple(ZONES.keys()))
        self.assertEqual(optional_spot_ids_for_region(DEFAULT_REGION_ID), tuple(OPTIONAL_ZONES.keys()))

    def test_visible_spots_returns_top_ranked_region_spots(self):
        ranked = ranked_spots_for_region(DEFAULT_REGION_ID)
        visible = visible_spots_for_region(DEFAULT_REGION_ID, limit=10)
        default_visible = visible_spots_for_region(DEFAULT_REGION_ID)

        self.assertEqual(len(visible), 10)
        self.assertEqual([spot["id"] for spot in visible], [spot["id"] for spot in ranked[:10]])
        self.assertTrue(all(DEFAULT_REGION_ID in spot["region_ids"] for spot in visible))
        self.assertEqual(len(default_visible), len(ranked))
        self.assertEqual([spot["id"] for spot in default_visible], [spot["id"] for spot in ranked])

    def test_visible_spots_clamps_to_region_size(self):
        visible = visible_spots_for_region(DEFAULT_REGION_ID, limit=999)

        self.assertEqual(len(visible), len(ALL_ZONES))

    def test_region_summaries_are_public_control_metadata(self):
        summaries = region_summaries()
        gig_harbor = summaries[0]

        self.assertEqual(gig_harbor["id"], DEFAULT_REGION_ID)
        self.assertEqual(gig_harbor["name"], "Gig Harbor")
        self.assertEqual(gig_harbor["default_spot_limit"], len(ALL_ZONES))
        self.assertEqual(gig_harbor["spot_count"], len(ALL_ZONES))
        self.assertNotIn("provider_context", gig_harbor)

    def test_region_search_aliases_resolve_regions_and_nearby_places(self):
        aliases = {entry["normalized"]: entry for entry in region_search_aliases()}

        self.assertEqual(aliases["gig harbor"]["term"], "Gig Harbor")
        self.assertEqual(aliases["port orchard"]["region_id"], "port_orchard")
        self.assertEqual(aliases["aberdeen"]["region_id"], "aberdeen")
        self.assertEqual(aliases["tacoma narrows"]["region_id"], "tacoma_narrows")
        self.assertEqual(aliases["union"]["region_id"], "south_hood_canal")
        self.assertEqual(aliases["belfair"]["region_id"], "south_hood_canal")
        self.assertEqual(aliases["chico"]["region_id"], "silverdale")
        self.assertEqual(aliases["gorst"]["region_id"], "bremerton")
        self.assertIn("Using South Hood Canal", aliases["belfair"]["note"])
        self.assertIn("Using Silverdale", aliases["chico"]["note"])

    def test_resolve_region_query_normalizes_common_place_text(self):
        self.assertEqual(resolve_region_query(" Port Orchard ")["region_id"], "port_orchard")
        self.assertEqual(resolve_region_query("Budd-Inlet")["region_id"], "olympia_budd_inlet")
        self.assertEqual(resolve_region_query("Gorst")["region_id"], "bremerton")
        self.assertIsNone(resolve_region_query(""))

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
                self.assertEqual(summaries[region_id]["default_spot_limit"], len(region["spot_ids"]))
                self.assertEqual(len(visible_spots_for_region(region_id)), len(region["spot_ids"]))
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
        self.assertEqual(context["provider_confidence"]["label"], "Subordinate station fit")

    def test_south_hood_canal_uses_sparse_current_strategy(self):
        context = provider_context_for_region("south_hood_canal")

        self.assertEqual(context["provider_strategy"]["profile"], "sparse_current")
        self.assertEqual(context["provider_strategy"]["headline"], "Sparse current coverage")
        self.assertEqual(context["provider_confidence"]["level"], "Medium")
        self.assertEqual(context["provider_confidence"]["label"], "Sparse current coverage")
        self.assertEqual(context["provider_strategy"]["tide_priority"][0]["station"], "9445478")
        self.assertEqual(context["provider_strategy"]["tide_priority"][1]["station"], "9445441")
        self.assertEqual(context["provider_strategy"]["current_priority"][0]["station"], "PUG1601")
        self.assertEqual(context["provider_strategy"]["current_priority"][1]["station"], "PUG1602")
        self.assertEqual(context["provider_strategy"]["current_priority"][-1]["mode"], "derived")
        self.assertTrue(context["provider_strategy"]["warnings"])

    def test_aberdeen_uses_coastal_provider_context(self):
        context = provider_context_for_region("aberdeen")

        self.assertEqual(context["nws_zone"], "PZZ110")
        self.assertEqual(context["tide_station_name"], "Aberdeen")
        self.assertEqual(context["current_station_name"], "Grays Harbor Entrance")
        self.assertEqual(context["current_station_type"], "S")
        self.assertEqual(context["provider_confidence"]["level"], "Medium")
        self.assertEqual(context["provider_confidence"]["label"], "River/bar influenced")
        self.assertEqual(context["provider_strategy"]["profile"], "river_bar_influenced")
        self.assertEqual(context["provider_strategy"]["current_priority"][-1]["mode"], "derived")
        self.assertTrue(any("bar" in warning for warning in context["provider_strategy"]["warnings"]))

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
