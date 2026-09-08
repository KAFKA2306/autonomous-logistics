import hashlib
import json
import unittest
from pathlib import Path

from autonomous_logistics import validate_geography_points

ROOT = Path(__file__).resolve().parent


class GeographyPointContractTest(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((ROOT / "data" / "registry.json").read_text())
        self.points = json.loads((ROOT / "data" / "geography-points.json").read_text())

    def test_only_exact_current_canonical_places_are_mapped(self):
        validate_geography_points(self.points, self.registry)
        names = {row["canonical_geography"] for row in self.points["records"]}
        self.assertEqual(
            names,
            {
                "Christiansburg, Virginia",
                "Pendleton, Oregon",
                "Charlotte, North Carolina",
                "Holly Springs, North Carolina",
                "Raeford, North Carolina",
                "Murphy, Texas",
                "Midland, Texas",
                "Monahans, Texas",
            },
        )
        self.assertTrue(names.isdisjoint(self.points["unmapped_boundary_examples"]))

    def test_census_source_records_are_hash_fixed(self):
        for row in self.points["records"]:
            digest = hashlib.sha256((row["source_record"] + "\n").encode()).hexdigest()
            self.assertEqual(digest, row["source_record_sha256"])
            self.assertTrue(row["source_url"].startswith("https://www2.census.gov/"))

    def test_dashboard_uses_canonical_geography_api_and_states_boundary(self):
        page = (ROOT / "web" / "index.html").read_text()
        self.assertIn("loadJson('geography-points.json')", page)
        self.assertIn("公式座標付き地域", page)
        self.assertIn("点は配送範囲・走行ルート・施設境界ではありません", page)
        self.assertNotIn("Pea Ridge city", page)


if __name__ == "__main__":
    unittest.main()
