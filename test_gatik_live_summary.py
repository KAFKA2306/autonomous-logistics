import unittest

from autonomous_logistics import parse_gatik_live_operations


class GatikLiveSummaryTests(unittest.TestCase):
    def test_displayed_status_counts_match_only_displayed_rows(self):
        text = (
            "Gatik Live Operations Pacific Standard Time (PST) "
            "Truck Start Time End Time Driving Time Stops Status "
            "G-001A 9:40 AM 10:48 AM 0:52 hrs Completed Completed "
            "G-002A 11:00 AM 1:10 PM 1:05 hrs Parked Ready "
            "Load more"
        )

        result = parse_gatik_live_operations(text)

        self.assertEqual(result["displayed_row_count"], 2)
        self.assertFalse(result["displayed_rows_complete"])
        self.assertEqual(
            result["displayed_status_counts"],
            {"On Time": 0, "Completed": 1, "Ready": 1},
        )
        self.assertEqual(sum(result["displayed_status_counts"].values()), 2)


if __name__ == "__main__":
    unittest.main()
