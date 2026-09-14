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

    def test_declined_write_does_not_run_the_tool(self):
        responses = [
            FakeResponse(
                tool_calls=[FakeToolCall("create_task", {"title": "Buy milk"})]
            ),
            FakeResponse(content="I did not add that task."),
        ]
        mock_create_task = MagicMock()

        with patch("agent.agent.chat", side_effect=responses), patch(
            "agent.agent.request_confirmation", return_value=False
        ) as mock_confirm, patch.dict(
            "agent.agent.TOOL_REGISTRY", {"create_task": mock_create_task}
        ):
            agent = Agent(model="test-model", system_prompt="test")
            result = agent.chat("Add buy milk to my tasks")

        mock_confirm.assert_called_once()
        mock_create_task.assert_not_called()
        self.assertEqual(result, "I did not add that task.")
    def test_on_tool_runs_after_automatic_tools_are_allowed(self):
        responses = [
            FakeResponse(tool_calls=[FakeToolCall("calculator", {"expression": "2 + 2"})]),
            FakeResponse(content="The answer is 4."),
        ]
        on_tool = MagicMock()

        with patch("agent.agent.chat", side_effect=responses):
            agent = Agent(model="test-model", system_prompt="test", on_tool=on_tool)
            agent.chat("What is 2 + 2?")

        on_tool.assert_called_once_with("calculator", {"expression": "2 + 2"})

    def test_injected_confirm_can_block_a_write(self):
        responses = [
            FakeResponse(
                tool_calls=[FakeToolCall("create_task", {"title": "Buy milk"})]
            ),
            FakeResponse(content="I did not add that task."),
        ]
        mock_create_task = MagicMock()
        confirm = MagicMock(return_value=False)

        with patch("agent.agent.chat", side_effect=responses), patch.dict(
            "agent.agent.TOOL_REGISTRY", {"create_task": mock_create_task}
        ):
            agent = Agent(
                model="test-model",
                system_prompt="test",
                confirm=confirm,
            )
            agent.chat("Add buy milk to my tasks")

        confirm.assert_called_once()
        mock_create_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
