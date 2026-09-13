from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from tools.dates import parse_datetime, resolve_day


FIXED_NOW = datetime(2026, 9, 13, 15, 36, tzinfo=timezone(timedelta(hours=-4)))


class DateHelperTests(unittest.TestCase):
    @patch("tools.dates.local_now", return_value=FIXED_NOW)
    def test_resolve_relative_days(self, _mock_now):
        self.assertEqual(resolve_day("today").isoformat(), "2026-09-13")
        self.assertEqual(resolve_day("tomorrow").isoformat(), "2026-09-14")
        self.assertEqual(resolve_day("2026-09-20").isoformat(), "2026-09-20")

    def test_parse_datetime_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            parse_datetime("next Friday")
        with self.assertRaises(ValueError):
            parse_datetime("")


if __name__ == "__main__":
    unittest.main()
