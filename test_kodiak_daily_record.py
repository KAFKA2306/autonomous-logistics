import json
import unittest
from pathlib import Path


class KodiakDailyRecordTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(Path("data/registry.json").read_text())

    def test_december_2024_atlas_launch_and_january_2025_snapshot_match_primary_source(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        launch = events["kodiak-launch-2024"]
        snapshot = events["kodiak-atlas-2025-01-24"]

        self.assertEqual(launch["effective_at"], "2024-12-18")
        self.assertEqual(launch["event_type"], "commercial_service_start")
        self.assertEqual(launch["operation_status"], "commercial_driverless")
        self.assertEqual(launch["customer"], "Atlas Energy Solutions")
        self.assertEqual(launch["driverless_trucks"], 2)
        self.assertEqual(launch["source_id"], "kodiak-atlas-commercial-start-2025")

        self.assertEqual(snapshot["effective_at"], "2025-01-24")
        self.assertEqual(snapshot["event_type"], "commercial_operation_snapshot")
        self.assertEqual(snapshot["customer"], "Atlas Energy Solutions")
        self.assertEqual(snapshot["driverless_trucks"], 2)
        self.assertEqual(snapshot["loads_cumulative"], 100)
        self.assertNotIn("loads_cumulative_qualifier", snapshot)
        self.assertEqual(snapshot["source_id"], "kodiak-atlas-commercial-start-2025")

        sources = {row["source_id"]: row for row in self.registry["sources"]}
        source = sources["kodiak-atlas-commercial-start-2025"]
        self.assertIn("January 24, 2025", source["required_markers"])
        self.assertIn("completed the delivery of 100 loads of proppant", source["required_markers"])
        self.assertIn("driverless service with these trucks commenced on December 18th, 2024", source["required_markers"])

    def test_june_2025_atlas_metrics_match_primary_source(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["kodiak-scale-2025"]
        self.assertEqual(event["effective_at"], "2025-06-10")
        self.assertEqual(event["operation_status"], "commercial_driverless")
        self.assertEqual(event["customer"], "Atlas Energy Solutions")
        self.assertEqual(event["driverless_trucks"], 4)
        self.assertEqual(event["loads_cumulative"], 800)
        self.assertEqual(event["loads_cumulative_qualifier"], "over")
        self.assertEqual(event["driverless_hours_cumulative"], 1600)
        self.assertEqual(event["driverless_hours_cumulative_qualifier"], "over")
        self.assertEqual(event["service_availability"], "up to 24/7")
        self.assertEqual(event["geography"], ["Permian Basin"])
        self.assertEqual(event["source_id"], "kodiak-2025-commercial")

        sources = {row["source_id"]: row for row in self.registry["sources"]}
        source = sources["kodiak-2025-commercial"]
        self.assertIn(
            "Atlas now owns and operates four trucks equipped with the Kodiak Driver",
            source["required_markers"],
        )
        self.assertIn("over 800 loads", source["required_markers"])
        self.assertIn("over 1,600 hours of driverless service", source["required_markers"])

    def test_july_20_2026_daily_record_matches_primary_source(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["kodiak-daily-record-2026-07-20"]
        self.assertEqual(event["effective_at"], "2026-07-20")
        self.assertEqual(event["event_type"], "commercial_operation_snapshot")
        self.assertEqual(event["operation_status"], "commercial_driverless")
        self.assertEqual(event["operator_id"], "kodiak")
        self.assertEqual(event["loads_single_day"], 176)
        self.assertEqual(event["geography"], ["Permian Basin"])
        self.assertEqual(event["source_id"], "kodiak-atlas-expansion-2026")

        sources = {row["source_id"]: row for row in self.registry["sources"]}
        source = sources["kodiak-atlas-expansion-2026"]
        self.assertIn("176 loads of sand in a single day", source["required_markers"])
        self.assertIn("all-time daily high", source["required_markers"])

    def test_q1_company_and_atlas_metrics_keep_separate_scope(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        company = events["kodiak-company-2026-q1"]
        atlas = events["kodiak-atlas-2026-q1"]

        self.assertEqual(company["effective_at"], "2026-03-31")
        self.assertEqual(company["loads_cumulative"], 15600)
        self.assertEqual(company["loads_cumulative_qualifier"], "more than")
        self.assertNotIn("customer", company)
        self.assertEqual(company["source_id"], "kodiak-q1-2026")

        self.assertEqual(atlas["effective_at"], "2026-03-31")
        self.assertEqual(atlas["customer"], "Atlas Energy Solutions")
        self.assertEqual(atlas["loads_cumulative"], 7000)
        self.assertEqual(atlas["loads_cumulative_qualifier"], "approximately")
        self.assertEqual(atlas["routes"], 15)
        self.assertEqual(atlas["freight_tons_cumulative"], 450000)
        self.assertEqual(atlas["source_id"], "kodiak-atlas-expansion-2026")

    def test_q2_company_metrics_do_not_inherit_atlas_scope(self):
        operators = {row["operator_id"]: row for row in self.registry["trucking_operators"]}
        kodiak = operators["kodiak"]
        snapshot = kodiak["current_snapshot"]
        self.assertNotIn("customer", kodiak)
        self.assertEqual(snapshot["as_of"], "2026-06-30")
        self.assertEqual(snapshot["customer_owned_driverless_vehicles"], 35)
        self.assertEqual(snapshot["paid_driverless_hours_cumulative"], 40000)
        self.assertEqual(snapshot["loads_cumulative"], 20000)
        self.assertNotIn("simultaneous_loadout_points", snapshot)
        self.assertNotIn("dune_express_miles", snapshot)

        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        atlas = events["kodiak-atlas-2026-q2"]
        self.assertEqual(atlas["customer"], "Atlas Energy Solutions")
        self.assertEqual(atlas["simultaneous_loadout_points"], 2)
        self.assertEqual(atlas["dune_express_miles"], 42)


if __name__ == "__main__":
    unittest.main()
