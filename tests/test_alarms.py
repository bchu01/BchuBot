import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tools.alarms import (
    cancel_alarm,
    fired_message,
    list_alarms,
    process_due,
    set_alarm,
    set_timer,
    stop_scheduler,
)


FIXED_NOW = datetime(2026, 9, 16, 17, 0, tzinfo=timezone(timedelta(hours=-4)))


class AlarmTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "alarms.sqlite"
        os.environ["BCHUBOT_ALARMS_DB"] = str(self.db_path)
        os.environ["BCHUBOT_ALARMS_SCHEDULER"] = "0"
        os.environ["BCHUBOT_ALARMS_NOTIFY"] = "0"
        stop_scheduler()

    def tearDown(self):
        stop_scheduler()
        os.environ.pop("BCHUBOT_ALARMS_DB", None)
        os.environ.pop("BCHUBOT_ALARMS_SCHEDULER", None)
        os.environ.pop("BCHUBOT_ALARMS_NOTIFY", None)
        self.temp_dir.cleanup()

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_set_timer_and_list(self, _mock_now):
        result = set_timer(minutes=10, label="Tea")
        self.assertTrue(result["ok"])
        self.assertEqual(result["alarm"]["kind"], "timer")
        self.assertEqual(result["alarm"]["status"], "pending")
        self.assertEqual(result["alarm"]["label"], "Tea")

        listed = list_alarms()
        self.assertEqual(len(listed["alarms"]), 1)
        self.assertEqual(listed["alarms"][0]["id"], result["alarm"]["id"])

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_timer_requires_a_duration(self, _mock_now):
        result = set_timer()
        self.assertEqual(
            result,
            {"ok": False, "error": "A timer must be at least one second."},
        )

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_timer_accepts_numeric_strings(self, _mock_now):
        result = set_timer(minutes="2", seconds="30", label="Pasta")
        self.assertTrue(result["ok"])
        due = datetime.fromisoformat(result["alarm"]["fires_at"])
        self.assertEqual(due, FIXED_NOW + timedelta(minutes=2, seconds=30))

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_timer_fires_when_due(self, mock_now):
        heard = []
        from tools.alarms import add_alarm_listener, remove_alarm_listener

        add_alarm_listener(heard.append)
        try:
            created = set_timer(minutes=5, label="Tea")
            mock_now.return_value = FIXED_NOW + timedelta(minutes=5)
            fired = process_due()
        finally:
            remove_alarm_listener(heard.append)

        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0]["id"], created["alarm"]["id"])
        self.assertEqual(fired[0]["status"], "fired")
        self.assertEqual(heard[0]["id"], created["alarm"]["id"])
        self.assertEqual(list_alarms()["alarms"], [])
        self.assertIn("Tea", fired_message(fired[0]))

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_late_item_is_marked_missed(self, mock_now):
        created = set_timer(minutes=5, label="Tea")
        mock_now.return_value = FIXED_NOW + timedelta(minutes=20)
        fired = process_due()
        self.assertEqual(fired[0]["id"], created["alarm"]["id"])
        self.assertEqual(fired[0]["status"], "missed")
        self.assertIn("Missed timer", fired_message(fired[0]))

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_cancel_prevents_firing(self, mock_now):
        created = set_timer(minutes=5, label="Tea")
        cancelled = cancel_alarm(alarm_id=created["alarm"]["id"])
        self.assertTrue(cancelled["ok"])
        mock_now.return_value = FIXED_NOW + timedelta(minutes=5)
        self.assertEqual(process_due(), [])

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_cancel_by_unique_label(self, _mock_now):
        set_timer(minutes=5, label="Tea")
        cancelled = cancel_alarm(label="tea")
        self.assertTrue(cancelled["ok"])
        self.assertEqual(list_alarms()["alarms"], [])

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_cancel_does_not_guess_when_label_is_ambiguous(self, _mock_now):
        set_timer(minutes=5, label="Tea")
        set_timer(minutes=8, label="Tea kettle")
        result = cancel_alarm(label="tea")
        self.assertFalse(result["ok"])
        self.assertIn("alarm_id", result["error"])
        self.assertEqual(len(list_alarms()["alarms"]), 2)

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_set_alarm_rolls_to_tomorrow_if_time_passed(self, _mock_now):
        result = set_alarm(time="9:00 AM", label="Wake")
        self.assertTrue(result["ok"])
        due = datetime.fromisoformat(result["alarm"]["fires_at"])
        self.assertEqual(due.date().isoformat(), "2026-09-17")
        self.assertEqual(due.hour, 9)

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_set_alarm_today_when_time_is_still_ahead(self, _mock_now):
        result = set_alarm(time="18:30", label="Dinner")
        self.assertTrue(result["ok"])
        due = datetime.fromisoformat(result["alarm"]["fires_at"])
        self.assertEqual(due.date().isoformat(), "2026-09-16")
        self.assertEqual(due.hour, 18)
        self.assertEqual(due.minute, 30)

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_explicit_past_day_is_rejected(self, _mock_now):
        result = set_alarm(time="9:00 AM", day="today", label="Wake")
        self.assertFalse(result["ok"])
        self.assertIn("already past", result["error"])

    @patch("tools.alarms.local_now", return_value=FIXED_NOW)
    def test_set_alarm_iso_when(self, _mock_now):
        result = set_alarm(when="2026-09-16T20:00", label="Call")
        self.assertTrue(result["ok"])
        due = datetime.fromisoformat(result["alarm"]["fires_at"])
        self.assertEqual(due.hour, 20)


if __name__ == "__main__":
    unittest.main()
