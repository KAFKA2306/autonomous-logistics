import json
import tempfile
import unittest
from pathlib import Path

from autonomous_logistics import build_api, dump, sha256, validate_registry, verify_manifest


class AutonomousLogisticsEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(Path("data/registry.json").read_text())

    def test_registry_has_current_faa_seven_and_three_trucking_operators(self):
        validate_registry(self.registry)
        self.assertEqual(len(self.registry["drone_part135"]), 7)
        self.assertGreaterEqual(len(self.registry["trucking_operators"]), 3)
        self.assertTrue(all(row["operation_status"] == "regulatory_authorization" for row in self.registry["drone_part135"]))
        self.assertTrue(all(row["operation_status"] == "commercial_driverless" for row in self.registry["trucking_operators"]))

    def test_missing_faa_area_is_explicit_not_inferred(self):
        for row in self.registry["drone_part135"]:
            self.assertIsNone(row["operating_area"])
            self.assertEqual(row["operating_area_status"], "not_listed_on_current_faa_page")

    def test_wing_houston_nepa_event_is_authorization_not_service_start(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["wing-houston-nepa-fonsi-2026"]
        self.assertEqual(event["effective_at"], "2026-08-18")
        self.assertEqual(event["event_type"], "environmental_authorization")
        self.assertEqual(event["operation_status"], "regulatory_authorization")
        self.assertEqual(event["operator_id"], "wing-aviation")
        self.assertEqual(event["source_id"], "faa-nepa-drone-operations")
        self.assertIn("Houston metropolitan area, Texas", event["geography"])

    def test_api_keeps_authorization_and_operation_status_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {
                "schema_version": 1,
                "retrieved_at": "2026-08-19T00:00:00+00:00",
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
                    }
                    for source in self.registry["sources"]
                ],
            }
            index = build_api(self.registry, manifest, root)
            drones = json.loads((root / "drone-part135.json").read_text())["records"]
            trucking = json.loads((root / "trucking.json").read_text())["records"]
            events = json.loads((root / "events.json").read_text())["records"]
        self.assertEqual(index["coverage"]["faa_part135_operator_count"], 7)
        self.assertEqual(index["coverage"]["commercial_driverless_trucking_operator_count"], 3)
        self.assertEqual(index["coverage"]["operation_event_count"], 7)
        self.assertEqual(index["coverage"]["operation_event_last_date"], "2026-08-18")
        self.assertTrue(all(row["operation_status"] == "regulatory_authorization" for row in drones))
        self.assertTrue(all(row["operation_status"] == "commercial_driverless" for row in trucking))
        wing_event = next(row for row in events if row["event_id"] == "wing-houston-nepa-fonsi-2026")
        self.assertEqual(wing_event["operation_status"], "regulatory_authorization")

    def test_raw_manifest_hash_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            objects = root / "raw" / "objects"
            objects.mkdir(parents=True)
            raw = b"primary source"
            digest = sha256(raw)
            path = objects / f"{digest}.html"
            path.write_bytes(raw)
            manifest = {
                "schema_version": 1,
                "retrieved_at": "2026-08-19T00:00:00+00:00",
                "sources": [{"source_id": "x", "evidence_path": path.relative_to(root).as_posix(), "sha256": digest}],
            }
            (root / "raw" / "latest-manifest.json").write_bytes(dump(manifest))
            self.assertEqual(verify_manifest(root)["sources"][0]["sha256"], digest)
            path.write_text("changed")
            with self.assertRaisesRegex(ValueError, "raw source hash mismatch"):
                verify_manifest(root)


if __name__ == "__main__":
    unittest.main()
