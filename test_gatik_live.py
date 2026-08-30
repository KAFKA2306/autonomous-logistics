import unittest

from autonomous_logistics import parse_gatik_live_operations


VALID = (
    "Everything below is live. These are real trips from our operations, refreshed every 3 hours. "
    "Live Operations Pacific Standard Time (PST) Updates in --:--:-- hrs "
    "Truck Start Time End Time Driving Time Stops Status "
    "G-001A 12:30 AM 2:07 AM 1:22 hrs Completed Completed "
    "G-002A 1:15 AM 8:00 AM 3:40 hrs Unloading On Time Load more"
)


class GatikLiveOperationsTests(unittest.TestCase):
    def test_parses_displayed_rows_without_promoting_them_to_complete_fleet(self):
        parsed = parse_gatik_live_operations(VALID)
        self.assertFalse(parsed["displayed_rows_complete"])
        self.assertEqual(parsed["displayed_row_count"], 2)
        self.assertEqual(parsed["refresh_interval_hours"], 3)
        self.assertEqual(parsed["time_zone_display"], "Pacific Standard Time (PST)")
        self.assertEqual(
            parsed["records"][1],
            {
                "truck_label": "G-002A",
                "start_time": "1:15 AM",
                "end_time": "8:00 AM",
                "driving_time": "3:40 hrs",
                "stops": "Unloading",
                "status": "On Time",
            },
        )

    def test_reordered_columns_fail_loudly(self):
        with self.assertRaisesRegex(ValueError, "columns are missing or reordered"):
            parse_gatik_live_operations(VALID.replace("Stops Status", "Status Stops"))

    def test_missing_truck_label_fails_loudly(self):
        broken = VALID.replace("G-002A ", "", 1)
        with self.assertRaisesRegex(ValueError, "row structure changed or a truck ID is missing"):
            parse_gatik_live_operations(broken)

    def test_unknown_status_fails_loudly(self):
        with self.assertRaisesRegex(ValueError, "unrecognized Gatik status value"):
            parse_gatik_live_operations(VALID.replace("Unloading On Time", "Unloading Unknown"))


if __name__ == "__main__":
    unittest.main()
