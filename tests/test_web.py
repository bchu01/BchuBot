import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["BCHUBOT_ALARMS_SCHEDULER"] = "0"
os.environ["BCHUBOT_ALARMS_NOTIFY"] = "0"

sys.modules.setdefault("ollama", MagicMock())

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

if TestClient is not None:
    from web.server import app
    from tools.alarms import process_due, set_timer


@unittest.skipUnless(TestClient, "fastapi is not installed")
class WebTests(unittest.TestCase):
    def test_index_serves_the_chat_page(self):
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("BchuBot", response.text)
        self.assertIn("/ws", response.text)
        self.assertIn('id="stats"', response.text)
        self.assertIn('id="stats-toggle"', response.text)
        self.assertIn("/stats", response.text)
        self.assertIn('id="progress"', response.text)
        self.assertIn('id="toast"', response.text)
        self.assertIn("notifyDone", response.text)
        self.assertIn('data.type === "token"', response.text)
        self.assertIn('data.type === "alarm"', response.text)

    def test_stats_endpoint_returns_usage(self):
        sample = {
            "cpu_percent": 18.0,
            "memory_used_gb": 23.77,
            "memory_total_gb": 24.0,
            "load_1m": 3.06,
            "cpu_count": 12,
            "ollama": {"cpu_percent": 40.0, "memory_mb": 512.0, "running": True},
            "bchubot": {"cpu_percent": 1.2, "memory_mb": 80.0, "running": True},
            "battery_c": 30.7,
        }
        with patch("web.server.collect_stats", return_value=sample):
            client = TestClient(app)
            response = client.get("/stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), sample)

    def test_websocket_returns_agent_reply(self):
        fake_agent = MagicMock()
        fake_agent.chat.return_value = "Hello from BchuBot"

        with patch("web.server.create_agent", return_value=fake_agent):
            client = TestClient(app)
            with client.websocket_connect("/ws") as websocket:
                websocket.send_json({"type": "message", "text": "Hi"})
                progress = websocket.receive_json()
                reply = websocket.receive_json()

        self.assertEqual(progress, {"type": "progress", "phase": "thinking"})
        self.assertEqual(reply, {"type": "reply", "text": "Hello from BchuBot"})
        fake_agent.chat.assert_called_once_with("Hi")

    def test_websocket_streams_tokens(self):
        def fake_create_agent(**kwargs):
            on_token = kwargs.get("on_token")
            fake_agent = MagicMock()

            def chat(_text):
                if on_token:
                    on_token("Hel")
                    on_token("lo")
                return "Hello"

            fake_agent.chat.side_effect = chat
            return fake_agent

        with patch("web.server.create_agent", side_effect=fake_create_agent):
            client = TestClient(app)
            with client.websocket_connect("/ws") as websocket:
                websocket.send_json({"type": "message", "text": "Hi"})
                messages = [websocket.receive_json() for _ in range(5)]

        types = [item["type"] for item in messages]
        self.assertEqual(types[0], "progress")
        self.assertIn("token", types)
        self.assertEqual(messages[-1], {"type": "reply", "text": "Hello"})
        texts = [item.get("text") for item in messages if item["type"] == "token"]
        self.assertEqual(texts, ["Hel", "lo"])

    def test_websocket_receives_local_alarm(self):
        db_dir = tempfile.TemporaryDirectory()
        self.addCleanup(db_dir.cleanup)
        os.environ["BCHUBOT_ALARMS_DB"] = str(Path(db_dir.name) / "alarms.sqlite")
        now = datetime(2026, 9, 16, 17, 0, tzinfo=timezone(timedelta(hours=-4)))
        fake_agent = MagicMock()
        fake_agent.chat.return_value = "Timer set."

        with patch("web.server.create_agent", return_value=fake_agent):
            client = TestClient(app)
            with client.websocket_connect("/ws") as websocket:
                with patch("tools.alarms.local_now", return_value=now):
                    created = set_timer(seconds=30, label="Tea")
                self.assertTrue(created["ok"])
                with patch(
                    "tools.alarms.local_now",
                    return_value=now + timedelta(seconds=30),
                ):
                    process_due()
                message = websocket.receive_json()

        self.assertEqual(message["type"], "alarm")
        self.assertIn("Tea", message["text"])
        self.assertEqual(message["status"], "fired")


if __name__ == "__main__":
    unittest.main()
