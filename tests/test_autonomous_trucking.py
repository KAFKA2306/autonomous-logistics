import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


DATA_PATH = Path(__file__).parents[1] / "data" / "autonomous-trucking-operations.json"


class AutonomousTruckingDataTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self.aurora = self.data["operators"][0]

    def test_aurora_commercial_service_and_latest_operations(self):
        self.assertEqual(self.data["schema_version"], 1)
        self.assertEqual(self.aurora["operator"], "Aurora Innovation, Inc.")
        self.assertEqual(self.aurora["mode"], "autonomous_trucking")

        service = self.aurora["commercial_service"]
        self.assertEqual(service["started_at"], "2025-04-27")
        self.assertTrue(service["driverless"])
        self.assertEqual(service["route"]["origin"], "Dallas, Texas")
        self.assertEqual(service["route"]["destination"], "Houston, Texas")
        self.assertEqual(service["customers"], ["Uber Freight", "Hirschbach Motor Lines"])

        observations = {(item["observed_at"], item["metric"]): item for item in self.aurora["operations"]}
        launch_miles = observations[("2025-05-01", "driverless_miles_since_launch")]
        self.assertEqual(launch_miles["value"], 1200)
        self.assertEqual(launch_miles["qualifier"], "more_than")

        latest_miles = observations[("2026-06-30", "driverless_miles_since_launch")]
        self.assertEqual(latest_miles["value"], 440000)
        self.assertEqual(latest_miles["qualifier"], "nearly")
        self.assertEqual(observations[("2026-06-30", "on_time_performance")]["value"], 100)
        self.assertEqual(observations[("2026-06-30", "aurora_driver_attributed_collisions")]["value"], 0)

    def test_sources_are_aurora_investor_relations_filings(self):
        urls = [self.aurora["commercial_service"]["source_url"]]
        urls.extend(item["source_url"] for item in self.aurora["operations"])
        for url in urls:
            parsed = urlparse(url)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "ir.aurora.tech")
            self.assertIn("/sec-filings/", parsed.path)


if __name__ == "__main__":
    unittest.main()
