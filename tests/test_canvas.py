import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tools.canvas import (
    CanvasConfigError,
    load_config,
    read_canvas_homework,
)


EASTERN = timezone(timedelta(hours=-4))
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=EASTERN)

CONFIG = {
    "base_url": "https://school.instructure.com",
    "access_token": "test-token",
}

UPCOMING = {
    "plannable_type": "assignment",
    "context_name": "CS 3200",
    "html_url": "https://school.instructure.com/courses/1/assignments/12",
    "submissions": {"submitted": False, "excused": False},
    "plannable": {
        "title": "Problem Set 3",
        "due_at": "2026-09-20T23:59:00-04:00",
        "points_possible": 100,
    },
}

OVERDUE = {
    "plannable_type": "assignment",
    "context_name": "ENGW 1111",
    "html_url": "https://school.instructure.com/courses/2/assignments/5",
    "submissions": {"submitted": False, "excused": False},
    "plannable": {
        "title": "Draft 1",
        "due_at": "2026-09-10T23:59:00-04:00",
        "points_possible": 25,
    },
}

SUBMITTED = {
    "plannable_type": "quiz",
    "context_name": "CS 3200",
    "submissions": {"submitted": True, "excused": False},
    "plannable": {
        "title": "Quiz 2",
        "due_at": "2026-09-19T12:00:00-04:00",
        "points_possible": 10,
    },
}

CALENDAR_EVENT = {
    "plannable_type": "calendar_event",
    "context_name": "CS 3200",
    "plannable": {
        "title": "Office hours",
        "due_at": "2026-09-19T15:00:00-04:00",
    },
}


def _write_config(directory, payload):
    path = Path(directory) / "canvas.json"
    path.write_text(json.dumps(payload))
    return path


class CanvasConfigTests(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(CanvasConfigError) as ctx:
            load_config("/tmp/bchubot-missing-canvas.json")
        self.assertIn("Canvas is not set up", str(ctx.exception))

    def test_loads_https_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _write_config(
                directory,
                {
                    "base_url": "https://school.instructure.com/api/v1",
                    "access_token": "abc123",
                },
            )
            config = load_config(path)
        self.assertEqual(
            config,
            {
                "base_url": "https://school.instructure.com",
                "access_token": "abc123",
            },
        )

    def test_rejects_http_base_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _write_config(
                directory,
                {"base_url": "http://school.instructure.com", "access_token": "abc"},
            )
            with self.assertRaises(CanvasConfigError) as ctx:
                load_config(path)
        self.assertIn("https", str(ctx.exception))

    def test_rejects_token_in_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _write_config(
                directory,
                {
                    "base_url": "https://user:secret@school.instructure.com",
                    "access_token": "abc",
                },
            )
            with self.assertRaises(CanvasConfigError) as ctx:
                load_config(path)
        self.assertIn("token", str(ctx.exception).lower())

    def test_requires_access_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = _write_config(
                directory,
                {"base_url": "https://school.instructure.com"},
            )
            with self.assertRaises(CanvasConfigError) as ctx:
                load_config(path)
        self.assertIn("access_token", str(ctx.exception))


class CanvasHomeworkTests(unittest.TestCase):
    def test_requires_valid_days(self):
        result = read_canvas_homework(days=0)
        self.assertEqual(
            result,
            {"ok": False, "error": "days must be between 1 and 60."},
        )
        result = read_canvas_homework(days="two")
        self.assertEqual(
            result,
            {"ok": False, "error": "days must be a whole number."},
        )

    @patch("tools.canvas.local_now", return_value=NOW)
    @patch("tools.canvas.load_config", return_value=CONFIG)
    @patch("tools.canvas._planner_items")
    def test_returns_upcoming_and_overdue(self, mock_items, _config, _now):
        mock_items.return_value = [UPCOMING, OVERDUE, SUBMITTED, CALENDAR_EVENT]

        result = read_canvas_homework()

        self.assertTrue(result["ok"])
        self.assertEqual(result["start"], "2026-09-18")
        self.assertEqual(result["end"], "2026-10-02")
        titles = [item["title"] for item in result["assignments"]]
        self.assertEqual(titles, ["Draft 1", "Problem Set 3"])
        self.assertTrue(result["assignments"][0]["overdue"])
        self.assertFalse(result["assignments"][1]["overdue"])
        self.assertEqual(result["assignments"][1]["course"], "CS 3200")
        self.assertEqual(result["assignments"][1]["points"], 100)
        self.assertNotIn("test-token", json.dumps(result))

    @patch("tools.canvas.local_now", return_value=NOW)
    @patch("tools.canvas.load_config", return_value=CONFIG)
    @patch("tools.canvas._planner_items")
    def test_filters_by_course(self, mock_items, _config, _now):
        mock_items.return_value = [UPCOMING, OVERDUE]

        result = read_canvas_homework(course="cs 3200")

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["assignments"]), 1)
        self.assertEqual(result["assignments"][0]["title"], "Problem Set 3")

    @patch("tools.canvas.local_now", return_value=NOW)
    @patch("tools.canvas.load_config", return_value=CONFIG)
    @patch("tools.canvas._planner_items")
    def test_days_window_excludes_later_work(self, mock_items, _config, _now):
        later = {
            "plannable_type": "assignment",
            "context_name": "CS 3200",
            "submissions": {"submitted": False},
            "plannable": {
                "title": "Project",
                "due_at": "2026-10-15T23:59:00-04:00",
            },
        }
        mock_items.return_value = [UPCOMING, later]

        result = read_canvas_homework(days=7)

        titles = [item["title"] for item in result["assignments"]]
        self.assertEqual(titles, ["Problem Set 3"])

    @patch("tools.canvas.load_config", return_value=CONFIG)
    @patch("tools.canvas._planner_items", side_effect=OSError("network down"))
    def test_network_failure(self, _items, _config):
        result = read_canvas_homework()
        self.assertEqual(
            result,
            {"ok": False, "error": "Could not read Canvas homework."},
        )
        self.assertNotIn("test-token", result["error"])

    @patch("tools.canvas.load_config", side_effect=CanvasConfigError(
        "Canvas is not set up. Save your Canvas site URL and access token "
        "to /Users/someone/.bchubot/canvas.json."
    ))
    def test_missing_setup(self, _config):
        result = read_canvas_homework()
        self.assertFalse(result["ok"])
        self.assertIn("Canvas is not set up", result["error"])


if __name__ == "__main__":
    unittest.main()
