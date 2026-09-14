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
        self.assertNotIn("recurrence", kwargs["body"])

    @patch("tools.calendar.calendar_service")
    def test_create_weekly_recurring_event(self, mock_service):
        service = _service_with_events(
            created={
                "id": "rec1",
                "summary": "Gym",
                "start": {"dateTime": "2026-09-14T18:00:00"},
                "end": {"dateTime": "2026-09-14T19:00:00"},
                "recurrence": ["RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE;COUNT=8"],
            }
        )
        mock_service.return_value = service

        result = create_calendar_event(
            title="Gym",
            start="2026-09-14T18:00",
            end="2026-09-14T19:00",
            recurrence="weekly",
            recurrence_days="Monday,Wednesday",
            recurrence_count=8,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["event"]["recurrence"],
            ["RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE;COUNT=8"],
        )
        body = service.events.return_value.insert.call_args.kwargs["body"]
        self.assertEqual(
            body["recurrence"],
            ["RRULE:FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE;COUNT=8"],
        )
        self.assertIn("timeZone", body["start"])

    @patch("tools.calendar.calendar_service")
    def test_create_rejects_invalid_recurrence(self, mock_service):
        result = create_calendar_event(
            title="Gym",
            start="2026-09-14T18:00",
            recurrence="hourly",
        )
        self.assertEqual(
            result,
            {
                "ok": False,
                "error": "Recurrence must be daily, weekly, monthly, or yearly.",
            },
        )
        mock_service.assert_not_called()

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
                "error": "An event_id, event_ids, or title is required to delete.",
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

    @patch("tools.calendar.calendar_service")
    def test_delete_scope_all_uses_series_id(self, mock_service):
        occurrence = dict(DENTIST, id="abc_20260914", recurringEventId="abc")
        service = _service_with_events(existing=occurrence)
        mock_service.return_value = service

        result = delete_calendar_event(event_id="abc_20260914", scope="all")

        self.assertTrue(result["ok"])
        self.assertEqual(result["scope"], "all")
        self.assertEqual(result["deleted"]["deleted_id"], "abc")
        kwargs = service.events.return_value.delete.call_args.kwargs
        self.assertEqual(kwargs["eventId"], "abc")

    @patch("tools.calendar.calendar_service")
    def test_delete_multiple_event_ids(self, mock_service):
        service = _service_with_events(existing=DENTIST)
        mock_service.return_value = service

        result = delete_calendar_event(event_ids="abc,def")

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["deleted"]), 2)
        self.assertEqual(service.events.return_value.delete.call_count, 2)

    def test_delete_rejects_invalid_scope(self):
        result = delete_calendar_event(event_id="abc", scope="maybe")
        self.assertEqual(
            result,
            {"ok": False, "error": "Scope must be 'this' or 'all'."},
        )


if __name__ == "__main__":
    unittest.main()
