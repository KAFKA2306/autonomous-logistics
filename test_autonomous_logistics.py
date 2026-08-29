import json
import tempfile
import unittest
from pathlib import Path

from autonomous_logistics import (
    build_api,
    dump,
    event_period_key,
    sha256,
    validate_registry,
    verify_manifest,
)


class AutonomousLogisticsEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(Path("data/registry.json").read_text())

    def test_registry_has_seven_faa_listed_and_three_trucking_operators(self):
        validate_registry(self.registry)
        drones = self.registry["drone_part135"]
        self.assertEqual(len(drones), 7)
        self.assertEqual(
            {row["operator_id"] for row in drones},
            {
                "wing-aviation",
                "ups-flight-forward",
                "amazon-prime-air",
                "zipline",
                "causey-aviation-unmanned",
                "droneup",
                "drone-express",
            },
        )
        self.assertNotIn("flytrex", {row["operator_id"] for row in drones})
        self.assertNotIn("doordash-air", {row["operator_id"] for row in drones})
        self.assertGreaterEqual(len(self.registry["trucking_operators"]), 3)
        self.assertTrue(
            all(row["operation_status"] == "regulatory_authorization" for row in drones)
        )
        self.assertTrue(
            all(
                row["operation_status"] == "commercial_driverless"
                for row in self.registry["trucking_operators"]
            )
        )

    def test_faa_certificate_period_preserves_source_precision(self):
        periods = {
            row["operator_id"]: row["part135_certificate_period"]
            for row in self.registry["drone_part135"]
        }
        self.assertEqual(
            periods,
            {
                "wing-aviation": "2019-04",
                "ups-flight-forward": "2019-09",
                "amazon-prime-air": "2020-08",
                "zipline": "2022-06",
                "causey-aviation-unmanned": "2023-01",
                "droneup": "2024-11",
                "drone-express": "2025-04",
            },
        )
        self.assertTrue(
            all(
                "part135_certificate_date" not in row
                for row in self.registry["drone_part135"]
            )
        )

    def test_missing_faa_area_is_explicit_not_inferred(self):
        for row in self.registry["drone_part135"]:
            self.assertIsNone(row["operating_area"])
            self.assertEqual(
                row["operating_area_status"],
                "not_listed_as_current_operating_area_on_faa_page",
            )

    def test_doordash_authorization_is_preserved_without_promoting_faa_registry_or_operation(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["doordash-air-part135-announcement-2026"]
        self.assertEqual(event["effective_at"], "2026-07-29")
        self.assertEqual(event["event_type"], "regulatory_authorization_announcement")
        self.assertEqual(event["operation_status"], "regulatory_authorization")
        self.assertEqual(event["operator_id"], "doordash-air")
        self.assertEqual(event["source_id"], "doordash-air-part135-2026")
        self.assertNotIn(
            "doordash-air",
            {row["operator_id"] for row in self.registry["drone_part135"]},
        )
        self.assertFalse(
            any(
                row.get("operator_id") == "doordash-air"
                and row.get("operation_status") == "commercial"
                for row in self.registry["operation_events"]
            )
        )

    def test_faa_commercial_service_events_preserve_month_precision(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        expected = {
            "ups-commercial-start-2019": ("2019-09", "ups-flight-forward"),
            "amazon-commercial-start-2020": ("2020-08", "amazon-prime-air"),
            "zipline-commercial-start-2022": ("2022-06", "zipline"),
            "causey-commercial-start-2023": (
                "2023-01",
                "causey-aviation-unmanned",
            ),
            "droneup-commercial-start-2024": ("2024-11", "droneup"),
        }
        for event_id, (period, operator_id) in expected.items():
            with self.subTest(event_id=event_id):
                event = events[event_id]
                self.assertEqual(event["effective_at"], period)
                self.assertEqual(event["event_type"], "commercial_service_start")
                self.assertEqual(event["operation_status"], "commercial")
                self.assertEqual(event["operator_id"], operator_id)
                self.assertEqual(event["source_id"], "faa-part135-package-delivery")
        self.assertEqual(
            events["zipline-commercial-start-2022"]["geography"],
            ["Charlotte, North Carolina"],
        )
        self.assertEqual(
            events["causey-commercial-start-2023"]["geography"],
            ["Holly Springs, North Carolina", "Raeford, North Carolina"],
        )
        self.assertEqual(
            events["causey-commercial-start-2023"]["aircraft"], "Flytrex UAS"
        )
        self.assertNotIn("drone-express-commercial-start-2025", events)

    def test_wing_christiansburg_commercial_start_uses_exact_primary_date(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["wing-commercial-start-2019"]
        self.assertEqual(event["effective_at"], "2019-10-18")
        self.assertEqual(event["event_type"], "commercial_service_start")
        self.assertEqual(event["operation_status"], "commercial")
        self.assertEqual(event["operator_id"], "wing-aviation")
        self.assertEqual(event["geography"], ["Christiansburg, Virginia"])
        self.assertEqual(
            event["source_id"], "wing-christiansburg-commercial-start-2019"
        )

    def test_causey_80k_snapshot_is_observed_commercial_scale(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["causey-commercial-scale-2024-03"]
        self.assertEqual(event["effective_at"], "2024-03")
        self.assertEqual(event["event_type"], "commercial_operation_snapshot")
        self.assertEqual(event["operation_status"], "commercial")
        self.assertEqual(event["operator_id"], "causey-aviation-unmanned")
        self.assertEqual(event["deliveries_cumulative"], 80000)
        self.assertEqual(event["deliveries_cumulative_qualifier"], "over")
        self.assertEqual(event["recipient_scope"], "consumer homes in the U.S.")
        self.assertEqual(event["source_id"], "faa-ipa-causey-operations")
        self.assertNotIn("authorized_max_operations_per_day", event)

    def test_event_period_key_accepts_source_month_without_fabricating_day(self):
        self.assertEqual(event_period_key("2019-09"), (2019, 9, 0))
        self.assertEqual(event_period_key("2026-08-18"), (2026, 8, 18))
        with self.assertRaises(ValueError):
            event_period_key("2026-13")

    def test_wing_commercial_scale_is_observed_operation_not_authorization(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["wing-commercial-scale-2026-06-08"]
        self.assertEqual(event["effective_at"], "2026-06-08")
        self.assertEqual(event["event_type"], "commercial_operation_snapshot")
        self.assertEqual(event["operation_status"], "commercial")
        self.assertEqual(event["operator_id"], "wing-aviation")
        self.assertEqual(event["deliveries_cumulative"], 1000000)
        self.assertEqual(event["deliveries_cumulative_qualifier"], "well over")
        self.assertEqual(
            event["geography"],
            ["Dallas-Fort Worth", "Metro Atlanta", "Greater Houston"],
        )
        self.assertEqual(event["source_id"], "wing-commercial-scale-2026")
        self.assertNotIn("authorization_type", event)

    def test_wing_houston_nepa_event_is_authorization_not_service_start(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["wing-houston-nepa-fonsi-2026"]
        self.assertEqual(event["effective_at"], "2026-08-18")
        self.assertEqual(event["event_type"], "environmental_authorization")
        self.assertEqual(event["operation_status"], "regulatory_authorization")
        self.assertEqual(event["operator_id"], "wing-aviation")
        self.assertEqual(event["source_id"], "faa-nepa-drone-operations")
        self.assertIn("Houston metropolitan area, Texas", event["geography"])

    def test_zipline_pea_ridge_opspec_expansion_is_authorization_not_observed_scale(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["zipline-pea-ridge-opspec-expansion-2026"]
        self.assertEqual(event["effective_at"], "2026-03-24")
        self.assertEqual(event["event_type"], "environmental_authorization")
        self.assertEqual(event["operation_status"], "regulatory_authorization")
        self.assertEqual(event["operator_id"], "zipline")
        self.assertEqual(event["source_id"], "faa-nepa-drone-operations")
        self.assertEqual(event["prior_max_operations_per_day"], 100)
        self.assertEqual(event["authorized_max_operations_per_day"], 400)
        self.assertEqual(event["authorized_operating_hours"], "24 hours per day")
        self.assertTrue(event["holidays_authorized"])
        self.assertNotIn("deliveries_per_day", event)

    def test_zipline_2_5m_snapshot_is_observed_commercial_scale(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["zipline-commercial-scale-2026-07-14"]
        self.assertEqual(event["effective_at"], "2026-07-14")
        self.assertEqual(event["event_type"], "commercial_operation_snapshot")
        self.assertEqual(event["operation_status"], "commercial")
        self.assertEqual(event["operator_id"], "zipline")
        self.assertEqual(event["deliveries_cumulative"], 2500000)
        self.assertEqual(event["deliveries_cumulative_qualifier"], "more than")
        self.assertEqual(event["deliveries_last_year"], 1000000)
        self.assertEqual(event["us_flight_share_approx"], 0.70)
        self.assertEqual(event["us_flight_share_qualifier"], "roughly")
        self.assertEqual(event["source_id"], "zipline-commercial-scale-2026")
        self.assertNotIn("authorized_max_operations_per_day", event)

    def test_zipline_2_7m_snapshot_updates_scale_without_promoting_future_uber_deployment(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["zipline-commercial-scale-2026-08-17"]
        self.assertEqual(event["effective_at"], "2026-08-17")
        self.assertEqual(event["event_type"], "commercial_operation_snapshot")
        self.assertEqual(event["operation_status"], "commercial")
        self.assertEqual(event["operator_id"], "zipline")
        self.assertEqual(event["deliveries_cumulative"], 2700000)
        self.assertEqual(event["deliveries_cumulative_qualifier"], "more than")
        self.assertEqual(event["commercial_autonomous_miles_cumulative"], 135000000)
        self.assertEqual(
            event["commercial_autonomous_miles_cumulative_qualifier"],
            "more than",
        )
        self.assertEqual(event["source_id"], "uber-zipline-partnership-2026")
        self.assertFalse(
            any(
                row.get("operator_id") == "uber"
                for row in self.registry["operation_events"]
            )
        )

    def test_kodiak_q2_2026_snapshot_uses_paid_driverless_metrics(self):
        trucks = {
            row["operator_id"]: row for row in self.registry["trucking_operators"]
        }
        kodiak = trucks["kodiak"]
        snapshot = kodiak["current_snapshot"]
        self.assertEqual(snapshot["as_of"], "2026-06-30")
        self.assertEqual(snapshot["customer_owned_driverless_vehicles"], 35)
        self.assertEqual(snapshot["paid_driverless_hours_cumulative"], 40000)
        self.assertEqual(
            snapshot["paid_driverless_hours_cumulative_qualifier"], "surpassed"
        )
        self.assertEqual(snapshot["loads_cumulative"], 20000)
        self.assertEqual(snapshot["loads_cumulative_qualifier"], "exceeded")
        self.assertEqual(snapshot["freight_tons_q2_2026"], 300000)
        self.assertEqual(snapshot["freight_tons_q2_2026_qualifier"], "more than")
        self.assertEqual(kodiak["source_id"], "kodiak-q2-2026")
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["kodiak-scale-2026-q2"]
        self.assertEqual(event["effective_at"], "2026-06-30")
        self.assertEqual(event["event_type"], "commercial_operation_snapshot")
        self.assertEqual(event["operation_status"], "commercial_driverless")
        self.assertEqual(event["source_id"], "kodiak-q2-2026")

    def test_droneup_capacity_benchmark_remains_testing_evidence(self):
        events = {row["event_id"]: row for row in self.registry["operation_events"]}
        event = events["droneup-capacity-test-2024"]
        self.assertEqual(event["effective_at"], "2024-08-06")
        self.assertEqual(event["event_type"], "capacity_test_snapshot")
        self.assertEqual(event["operation_status"], "testing")
        self.assertEqual(event["deliveries_single_day"], 500)
        self.assertEqual(event["deliveries_per_hour"], 40)
        self.assertEqual(event["max_package_weight_lb"], 10)
        self.assertEqual(event["pilot_to_drone_ratio"], "one-to-many")
        self.assertEqual(event["source_id"], "droneup-capacity-test-2024")

    def test_month_only_faa_certifications_are_not_fabricated_as_day_events(self):
        event_ids = {row["event_id"] for row in self.registry["operation_events"]}
        self.assertNotIn("drone-express-part135-2024", event_ids)
        self.assertNotIn("flytrex-part135-2025", event_ids)

    def test_api_keeps_authorization_testing_and_operation_status_separate(self):
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
        self.assertEqual(
            index["coverage"]["commercial_driverless_trucking_operator_count"], 3
        )
        self.assertEqual(
            index["coverage"]["operation_event_count"],
            len(self.registry["operation_events"]),
        )
        self.assertEqual(
            index["coverage"]["primary_source_count"], len(self.registry["sources"])
        )
        self.assertEqual(index["coverage"]["operation_event_first_period"], "2019-09")
        self.assertEqual(index["coverage"]["operation_event_last_period"], "2026-08-18")
        self.assertEqual(
            index["coverage"]["events_2024_or_later"],
            sum(
                event_period_key(row["effective_at"]) >= (2024, 1, 0)
                for row in self.registry["operation_events"]
            ),
        )
        self.assertTrue(
            all(row["operation_status"] == "regulatory_authorization" for row in drones)
        )
        self.assertTrue(
            all(row["operation_status"] == "commercial_driverless" for row in trucking)
        )
        wing_start = next(
            row for row in events if row["event_id"] == "wing-commercial-start-2019"
        )
        wing_scale = next(
            row
            for row in events
            if row["event_id"] == "wing-commercial-scale-2026-06-08"
        )
        wing_event = next(
            row
            for row in events
            if row["event_id"] == "wing-houston-nepa-fonsi-2026"
        )
        zipline_event = next(
            row
            for row in events
            if row["event_id"] == "zipline-pea-ridge-opspec-expansion-2026"
        )
        zipline_scale = next(
            row
            for row in events
            if row["event_id"] == "zipline-commercial-scale-2026-07-14"
        )
        zipline_latest = next(
            row
            for row in events
            if row["event_id"] == "zipline-commercial-scale-2026-08-17"
        )
        doordash_event = next(
            row
            for row in events
            if row["event_id"] == "doordash-air-part135-announcement-2026"
        )
        causey_scale = next(
            row
            for row in events
            if row["event_id"] == "causey-commercial-scale-2024-03"
        )
        droneup_test = next(
            row for row in events if row["event_id"] == "droneup-capacity-test-2024"
        )
        droneup_service = next(
            row
            for row in events
            if row["event_id"] == "droneup-commercial-start-2024"
        )
        kodiak_scale = next(
            row for row in events if row["event_id"] == "kodiak-scale-2026-q2"
        )
        kodiak_truck = next(row for row in trucking if row["operator_id"] == "kodiak")
        self.assertEqual(wing_start["operation_status"], "commercial")
        self.assertEqual(wing_start["effective_at"], "2019-10-18")
        self.assertEqual(wing_scale["operation_status"], "commercial")
        self.assertEqual(wing_scale["deliveries_cumulative_qualifier"], "well over")
        self.assertEqual(wing_event["operation_status"], "regulatory_authorization")
        self.assertEqual(zipline_event["operation_status"], "regulatory_authorization")
        self.assertEqual(zipline_scale["operation_status"], "commercial")
        self.assertEqual(zipline_scale["deliveries_cumulative_qualifier"], "more than")
        self.assertEqual(zipline_latest["operation_status"], "commercial")
        self.assertEqual(zipline_latest["deliveries_cumulative"], 2700000)
        self.assertEqual(doordash_event["operation_status"], "regulatory_authorization")
        self.assertEqual(causey_scale["operation_status"], "commercial")
        self.assertEqual(causey_scale["deliveries_cumulative_qualifier"], "over")
        self.assertEqual(droneup_test["operation_status"], "testing")
        self.assertEqual(droneup_service["operation_status"], "commercial")
        self.assertEqual(kodiak_scale["operation_status"], "commercial_driverless")
        self.assertEqual(kodiak_truck["current_snapshot"]["loads_cumulative"], 20000)

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
                "sources": [
                    {
                        "source_id": "x",
                        "evidence_path": path.relative_to(root).as_posix(),
                        "sha256": digest,
                    }
                ],
            }
            (root / "raw" / "latest-manifest.json").write_bytes(dump(manifest))
            self.assertEqual(verify_manifest(root)["sources"][0]["sha256"], digest)
            path.write_text("changed")
            with self.assertRaisesRegex(ValueError, "raw source hash mismatch"):
                verify_manifest(root)


if __name__ == "__main__":
    unittest.main()