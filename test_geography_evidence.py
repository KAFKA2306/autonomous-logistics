import json
import unittest
from pathlib import Path


class GeographyEvidenceTests(unittest.TestCase):
    def test_aurora_driverless_route_uses_q2_2026_primary_source_geography(self):
        registry = json.loads(Path("data/registry.json").read_text())
        expected = [
            "Midland, Texas",
            "Monahans, Texas",
            "Interstate 20 between Midland and Monahans, Texas",
        ]
        truck = next(
            row for row in registry["trucking_operators"] if row["operator_id"] == "aurora"
        )
        event = next(
            row for row in registry["operation_events"] if row["event_id"] == "aurora-current-2026"
        )
        self.assertEqual(truck["geography"], expected)
        self.assertEqual(event["geography"], expected)
        self.assertEqual(truck["source_id"], "aurora-q2-2026")
        self.assertEqual(event["source_id"], "aurora-q2-2026")


if __name__ == "__main__":
    unittest.main()
