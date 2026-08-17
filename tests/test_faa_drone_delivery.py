import unittest

from src.collect_faa_drone_delivery import verify


class VerifyFaaDroneDeliveryTest(unittest.TestCase):
    def test_verify_requires_every_reviewed_operator_on_source_page(self):
        registry = {"operators": [{"operator": "Wing Aviation, LLC"}, {"operator": "Zipline International Inc."}]}
        raw = b"<html><body>Wing Aviation, LLC is listed here.</body></html>"
        with self.assertRaisesRegex(ValueError, "Zipline International"):
            verify(registry, raw)

    def test_verify_accepts_reviewed_names_and_records_hash(self):
        registry = {"operators": [{"operator": "Wing Aviation, LLC"}]}
        result = verify(registry, b"<p>Wing Aviation, LLC</p>")
        self.assertEqual(result["operator_count"], 1)
        self.assertEqual(len(result["source_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
