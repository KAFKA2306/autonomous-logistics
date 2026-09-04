import json
import tempfile
import unittest
from pathlib import Path

from autonomous_logistics import build_api


class Part135ReconciliationTests(unittest.TestCase):
    def test_operator_authorization_announcement_is_reconciled_with_faa_registry(self):
        registry = json.loads(Path("data/registry.json").read_text())
        manifest = json.loads(
            Path("api/v1/autonomous-logistics/provenance.json").read_text()
        )

        with tempfile.TemporaryDirectory() as tmp:
            api_dir = Path(tmp)
            index = build_api(registry, manifest, api_dir)
            reconciliation = json.loads(
                (api_dir / "part135-reconciliation.json").read_text()
            )

        self.assertEqual(
            index["coverage"]["part135_operator_announcements_not_listed_count"], 1
        )
        self.assertEqual(
            index["views"]["part135_reconciliation"],
            "part135-reconciliation.json",
        )
        self.assertEqual(reconciliation["faa_registry"]["listed_operator_count"], 7)
        self.assertEqual(len(reconciliation["records"]), 1)
        record = reconciliation["records"][0]
        self.assertEqual(record["operator_id"], "doordash-air")
        self.assertEqual(record["announcement_effective_at"], "2026-07-29")
        self.assertEqual(
            record["faa_registry_status"],
            "not_listed_on_current_faa_package_delivery_page",
        )
        self.assertEqual(record["operator_source_id"], "doordash-air-part135-2026")
        self.assertTrue(record["operator_source_url"].startswith("https://"))
        self.assertEqual(len(record["operator_source_sha256"]), 64)
        self.assertTrue(reconciliation["faa_registry"]["source_url"].startswith("https://"))
        self.assertEqual(len(reconciliation["faa_registry"]["source_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
