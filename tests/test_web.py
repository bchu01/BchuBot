import sys
import unittest
from unittest.mock import MagicMock, patch

sys.modules.setdefault("ollama", MagicMock())

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

if TestClient is not None:
    from web.server import app


@unittest.skipUnless(TestClient, "fastapi is not installed")
class WebTests(unittest.TestCase):
    def test_index_serves_the_chat_page(self):
        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("BchuBot", response.text)
        self.assertIn("/ws", response.text)

    def test_websocket_returns_agent_reply(self):
        fake_agent = MagicMock()
        fake_agent.chat.return_value = "Hello from BchuBot"

        with patch("web.server.create_agent", return_value=fake_agent):
            client = TestClient(app)
            with client.websocket_connect("/ws") as websocket:
                websocket.send_json({"type": "message", "text": "Hi"})
                status = websocket.receive_json()
                reply = websocket.receive_json()

        self.assertEqual(status["type"], "status")
        self.assertEqual(reply, {"type": "reply", "text": "Hello from BchuBot"})
        fake_agent.chat.assert_called_once_with("Hi")


if __name__ == "__main__":
    unittest.main()
