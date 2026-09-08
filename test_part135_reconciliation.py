import json
import tempfile
import unittest
from pathlib import Path

from autonomous_logistics import build_api


class Part135ReconciliationTests(unittest.TestCase):
    def test_operator_authorization_announcement_is_reconciled_with_faa_registry(self):
        registry = json.loads(Path("data/registry.json").read_text())
        manifest = {
            "schema_version": 1,
            "retrieved_at": "2026-09-09T00:00:00+00:00",
            "sources": [
                {
                    "source_id": source["source_id"],
                    "authority": source["authority"],
                    "source_url": source["source_url"],
                    "sha256": "a" * 64,
                    "size_bytes": 1,
                    "content_type": "text/html",
                    "evidence_path": f"raw/objects/{source['source_id']}.html",
                    "verified_markers": source["required_markers"],
                    **(
                        {
                            "structured_data": {
                                "time_zone_display": "Pacific Standard Time (PST)",
                                "refresh_interval_hours": 3,
                                "displayed_rows_complete": False,
                                "displayed_row_count": 0,
                                "displayed_status_counts": {},
                                "records": [],
                            }
                        }
                        if source.get("parser") == "gatik_live_operations"
                        else {}
                    ),
                }
                for source in registry["sources"]
            ],
        }

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
