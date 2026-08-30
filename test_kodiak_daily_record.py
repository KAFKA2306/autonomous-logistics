import json
import unittest
from pathlib import Path


class KodiakDailyRecordTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(Path("data/registry.json").read_text())

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
