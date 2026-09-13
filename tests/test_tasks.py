import unittest
from unittest.mock import MagicMock, patch

from tools.agenda import read_today
from tools.tasks import create_task, create_task_list, read_task_lists, read_tasks


def _tasks_service(lists=None, tasks=None, created_task=None, created_list=None):
    service = MagicMock()
    service.tasklists.return_value.list.return_value.execute.return_value = {
        "items": lists or []
    }
    service.tasks.return_value.list.return_value.execute.return_value = {
        "items": tasks or []
    }
    service.tasks.return_value.insert.return_value.execute.return_value = (
        created_task or {}
    )
    service.tasklists.return_value.insert.return_value.execute.return_value = (
        created_list or {}
    )
    return service


class TasksTests(unittest.TestCase):
    @patch("tools.tasks.tasks_service")
    def test_read_task_lists(self, mock_service):
        mock_service.return_value = _tasks_service(
            lists=[{"id": "1", "title": "Personal"}]
        )
        result = read_task_lists()
        self.assertEqual(result["lists"], [{"id": "1", "title": "Personal"}])

    @patch("tools.tasks.tasks_service")
    def test_read_tasks_filters_due_date(self, mock_service):
        mock_service.return_value = _tasks_service(
            tasks=[
                {
                    "id": "a",
                    "title": "Buy milk",
                    "due": "2026-09-14T00:00:00.000Z",
                    "status": "needsAction",
                },
                {
                    "id": "b",
                    "title": "Later",
                    "due": "2026-09-20T00:00:00.000Z",
                    "status": "needsAction",
                },
            ]
        )
        result = read_tasks(due="2026-09-14")
        self.assertTrue(result["ok"])
        self.assertEqual([task["title"] for task in result["tasks"]], ["Buy milk"])

    @patch("tools.tasks.tasks_service")
    def test_create_task_requires_title(self, mock_service):
        result = create_task(title="")
        self.assertEqual(result, {"ok": False, "error": "A task title is required."})
        mock_service.assert_not_called()

    @patch("tools.tasks.tasks_service")
    def test_create_task_and_list(self, mock_service):
        service = _tasks_service(
            created_task={"id": "t1", "title": "Email Sam", "status": "needsAction"},
            created_list={"id": "l1", "title": "Groceries"},
        )
        mock_service.return_value = service

        task = create_task(title="Email Sam", due="2026-09-14")
        task_list = create_task_list(title="Groceries")

        self.assertTrue(task["ok"])
        self.assertEqual(task["task"]["title"], "Email Sam")
        self.assertTrue(task_list["ok"])
        self.assertEqual(task_list["list"]["title"], "Groceries")


class AgendaTests(unittest.TestCase):
    @patch("tools.agenda.read_tasks")
    @patch("tools.agenda.read_calendar")
    def test_read_today_combines_events_and_tasks(self, mock_calendar, mock_tasks):
        mock_calendar.return_value = {
            "ok": True,
            "start": "2026-09-14",
            "events": [{"title": "Dentist"}],
        }
        mock_tasks.return_value = {
            "ok": True,
            "tasks": [{"title": "Buy milk"}],
        }

        result = read_today()

        self.assertEqual(
            result,
            {
                "ok": True,
                "date": "2026-09-14",
                "events": [{"title": "Dentist"}],
                "tasks": [{"title": "Buy milk"}],
            },
        )
        mock_calendar.assert_called_once_with(start="today", end="today")
        mock_tasks.assert_called_once_with(due="today")


if __name__ == "__main__":
    unittest.main()
