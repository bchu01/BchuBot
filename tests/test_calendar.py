import unittest
from unittest.mock import MagicMock, patch

from tools.calendar import (
    create_calendar_event,
    create_reminder,
    delete_calendar_event,
    read_calendar,
)
from tools.google_auth import GoogleAuthError


DENTIST = {
    "id": "abc",
    "summary": "Dentist",
    "start": {"dateTime": "2026-09-14T09:00:00-04:00"},
    "end": {"dateTime": "2026-09-14T09:45:00-04:00"},
}


def _service_with_events(payload=None, created=None, existing=None):
    service = MagicMock()
    service.events.return_value.list.return_value.execute.return_value = payload or {
        "items": []
    }
    service.events.return_value.insert.return_value.execute.return_value = created or {}
    service.events.return_value.get.return_value.execute.return_value = existing or {}
    service.events.return_value.delete.return_value.execute.return_value = None
    return service


class CalendarTests(unittest.TestCase):
    @patch("tools.calendar.calendar_service")
    def test_read_calendar_formats_events(self, mock_service):
        mock_service.return_value = _service_with_events({"items": [DENTIST]})

        result = read_calendar(start="2026-09-14", end="2026-09-14")

        self.assertTrue(result["ok"])
        self.assertEqual(result["start"], "2026-09-14")
        self.assertEqual(result["events"][0]["title"], "Dentist")

    @patch("tools.calendar.calendar_service")
    def test_create_event_requires_title(self, mock_service):
        result = create_calendar_event(title="", start="2026-09-14T09:00")
        self.assertEqual(result, {"ok": False, "error": "An event title is required."})
        mock_service.assert_not_called()

    @patch("tools.calendar.calendar_service")
    def test_create_event_inserts_primary_calendar(self, mock_service):
        service = _service_with_events(
            created={
                "id": "evt1",
                "summary": "Lunch",
                "start": {"dateTime": "2026-09-14T12:00:00"},
                "end": {"dateTime": "2026-09-14T13:00:00"},
            }
        )
        mock_service.return_value = service

        result = create_calendar_event(
            title="Lunch",
            start="2026-09-14T12:00",
            end="2026-09-14T13:00",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["event"]["title"], "Lunch")
        service.events.return_value.insert.assert_called_once()
        kwargs = service.events.return_value.insert.call_args.kwargs
        self.assertEqual(kwargs["calendarId"], "primary")
        self.assertEqual(kwargs["body"]["summary"], "Lunch")

    @patch("tools.calendar.calendar_service")
    def test_create_reminder_uses_short_event(self, mock_service):
        service = _service_with_events(
            created={
                "id": "rem1",
                "summary": "Call Alex",
                "start": {"dateTime": "2026-09-14T15:00:00"},
                "end": {"dateTime": "2026-09-14T15:15:00"},
            }
        )
        mock_service.return_value = service

        result = create_reminder(title="Call Alex", when="2026-09-14T15:00")

        self.assertTrue(result["ok"])
        self.assertEqual(result["event"]["title"], "Call Alex")

    @patch("tools.calendar.calendar_service", side_effect=GoogleAuthError("not set up"))
    def test_read_calendar_reports_auth_error(self, _mock_service):
        result = read_calendar(start="2026-09-14")
        self.assertEqual(result, {"ok": False, "error": "not set up"})

    def test_delete_requires_id_or_title(self):
        result = delete_calendar_event()
        self.assertEqual(
            result,
            {
                "ok": False,
                "error": "An event_id or title is required to delete an event.",
            },
        )

    @patch("tools.calendar.calendar_service")
    def test_delete_by_event_id(self, mock_service):
        service = _service_with_events(existing=DENTIST)
        mock_service.return_value = service

        result = delete_calendar_event(event_id="abc")

        self.assertTrue(result["ok"])
        self.assertEqual(result["deleted"]["title"], "Dentist")
        service.events.return_value.delete.assert_called_once()
        kwargs = service.events.return_value.delete.call_args.kwargs
        self.assertEqual(kwargs["eventId"], "abc")
        self.assertEqual(kwargs["sendUpdates"], "all")

    @patch("tools.calendar.calendar_service")
    def test_delete_by_unique_title(self, mock_service):
        service = _service_with_events(payload={"items": [DENTIST]}, existing=DENTIST)
        mock_service.return_value = service

        result = delete_calendar_event(title="dentist", day="2026-09-14")

        self.assertTrue(result["ok"])
        self.assertEqual(result["deleted"]["id"], "abc")

    @patch("tools.calendar.calendar_service")
    def test_delete_does_not_guess_when_title_is_ambiguous(self, mock_service):
        second = dict(DENTIST, id="def", start={"dateTime": "2026-09-14T14:00:00-04:00"})
        service = _service_with_events(payload={"items": [DENTIST, second]})
        mock_service.return_value = service

        result = delete_calendar_event(title="Dentist", day="2026-09-14")

        self.assertFalse(result["ok"])
        self.assertIn("Multiple events", result["error"])
        service.events.return_value.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
