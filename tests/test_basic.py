from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from tools.basic import calculator, get_date, get_time


FIXED_NOW = datetime(2026, 9, 13, 15, 36, tzinfo=timezone(timedelta(hours=-4)))


class CalculatorTests(unittest.TestCase):
    def test_basic_arithmetic(self):
        self.assertEqual(calculator("17 * 24"), "408")
        self.assertEqual(calculator("(3 + 5) / 2"), "4")
        self.assertEqual(calculator("10 - 3"), "7")
        self.assertEqual(calculator("7 // 2"), "3")
        self.assertEqual(calculator("7 % 2"), "1")

    def test_unary_and_decimals(self):
        self.assertEqual(calculator("-4 + 1"), "-3")
        self.assertEqual(calculator("1.5 + 2.25"), "3.75")

    def test_rejects_empty_and_non_strings(self):
        self.assertEqual(calculator(""), "Unable to calculate that expression.")
        self.assertEqual(calculator("   "), "Unable to calculate that expression.")
        self.assertEqual(calculator(None), "Unable to calculate that expression.")
        self.assertEqual(calculator(12), "Unable to calculate that expression.")

    def test_rejects_code_and_names(self):
        self.assertEqual(
            calculator("__import__('os').system('echo hi')"),
            "Unable to calculate that expression.",
        )
        self.assertEqual(calculator("abs(1)"), "Unable to calculate that expression.")
        self.assertEqual(calculator("x + 1"), "Unable to calculate that expression.")

    def test_rejects_division_by_zero_and_huge_powers(self):
        self.assertEqual(calculator("1 / 0"), "Unable to calculate that expression.")
        self.assertEqual(calculator("2 ** 100"), "Unable to calculate that expression.")


class DateTimeTests(unittest.TestCase):
    @patch("tools.basic.datetime")
    def test_get_time_uses_local_clock(self, mock_datetime):
        mock_datetime.now.return_value = FIXED_NOW
        self.assertEqual(get_time(), "03:36 PM")

    @patch("tools.basic.datetime")
    def test_get_date_includes_weekday_and_iso(self, mock_datetime):
        mock_datetime.now.return_value = FIXED_NOW
        self.assertEqual(get_date(), "Sunday, September 13, 2026 (2026-09-13)")


if __name__ == "__main__":
    unittest.main()
