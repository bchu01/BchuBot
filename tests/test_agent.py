import sys
import unittest
from unittest.mock import MagicMock, patch

sys.modules.setdefault("ollama", MagicMock())

from agent.agent import Agent


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, name, arguments=None):
        self.function = FakeFunction(name, arguments or {})


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeResponse:
    def __init__(self, content=None, tool_calls=None):
        self.message = FakeMessage(content=content, tool_calls=tool_calls)


class AgentLoopTests(unittest.TestCase):
    def test_returns_final_message_after_tools(self):
        responses = [
            FakeResponse(tool_calls=[FakeToolCall("calculator", {"expression": "2 + 2"})]),
            FakeResponse(content="The answer is 4."),
        ]

        with patch("agent.agent.chat", side_effect=responses) as mock_chat:
            agent = Agent(model="test-model", system_prompt="test")
            result = agent.chat("What is 2 + 2?")

        self.assertEqual(result, "The answer is 4.")
        self.assertEqual(mock_chat.call_count, 2)

    def test_stops_after_max_tool_rounds(self):
        looping_response = FakeResponse(
            tool_calls=[FakeToolCall("calculator", {"expression": "1 + 1"})]
        )

        with patch("agent.agent.chat", return_value=looping_response) as mock_chat:
            agent = Agent(model="test-model", system_prompt="test", max_tool_rounds=2)
            result = agent.chat("Keep calculating")

        self.assertIn("maximum number of tool steps", result)
        self.assertEqual(mock_chat.call_count, 3)
        self.assertEqual(agent.messages[-1]["role"], "assistant")
        self.assertEqual(agent.messages[-1]["content"], result)


if __name__ == "__main__":
    unittest.main()
