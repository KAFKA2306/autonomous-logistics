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


if __name__ == "__main__":
    unittest.main()
