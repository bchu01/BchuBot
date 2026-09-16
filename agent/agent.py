import json
from collections.abc import Iterator
from types import SimpleNamespace

from ollama import chat
from tools.permissions import (
    CONFIRMATION_REQUIRED,
    DISABLED,
    permission_for,
    request_confirmation,
)
from tools.registry import TOOL_REGISTRY, TOOL_DEFINITIONS

DEFAULT_MAX_TOOL_ROUNDS = 12


class Agent:
    def __init__(
        self,
        model,
        system_prompt,
        max_tool_rounds=DEFAULT_MAX_TOOL_ROUNDS,
        confirm=None,
        on_tool=None,
        on_token=None,
        on_thinking=None,
        context_for_message=None,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.max_tool_rounds = max_tool_rounds
        self.confirm = confirm or request_confirmation
        self.on_tool = on_tool
        self.on_token = on_token
        self.on_thinking = on_thinking
        self.context_for_message = context_for_message
        self._turn_context = None

        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]

    def chat(self, user_input):
        self._turn_context = None
        if self.context_for_message:
            try:
                self._turn_context = self.context_for_message(user_input)
            except Exception:
                self._turn_context = None

        self.messages.append({
            "role": "user",
            "content": user_input
        })

        tool_rounds = 0

        while True:
            message = self._model_turn()

            if not message.tool_calls:
                assistant_message = message.content or ""

                self.messages.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                return assistant_message

            if tool_rounds >= self.max_tool_rounds:
                limit_message = (
                    "I reached the maximum number of tool steps for this "
                    "request and stopped without finishing."
                )
                self.messages.append({
                    "role": "assistant",
                    "content": limit_message
                })
                return limit_message

            self.messages.append(self._history_message(message))
            tool_rounds += 1

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name

                if tool_name not in TOOL_REGISTRY:
                    tool_result = f"Unknown tool: {tool_name}"

                else:
                    tool = TOOL_REGISTRY[tool_name]

                    arguments = tool_call.function.arguments

                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}

                    if not isinstance(arguments, dict):
                        arguments = {}

                    permission = permission_for(tool_name)
                    if permission == DISABLED:
                        tool_result = f"The {tool_name} tool is disabled."
                    elif (
                        permission == CONFIRMATION_REQUIRED
                        and not self.confirm(tool_name, arguments)
                    ):
                        tool_result = "The user declined this action."
                    else:
                        if self.on_tool:
                            self.on_tool(tool_name, arguments)
                        try:
                            tool_result = tool(**arguments)
                        except Exception as e:
                            tool_result = f"Tool error: {str(e)}"

                self.messages.append({
                    "role": "tool",
                    "content": str(tool_result)
                })

    def _model_turn(self):
        result = chat(
            model=self.model,
            messages=self._messages_for_model(),
            tools=TOOL_DEFINITIONS,
            stream=True,
        )
        if hasattr(result, "message") and not isinstance(result, Iterator):
            message = result.message
            if (
                self.on_token
                and message.content
                and not message.tool_calls
            ):
                self.on_token(message.content)
            return message
        return self._consume_stream(result)

    def _messages_for_model(self):
        if not self._turn_context or not self.messages:
            return self.messages
        head = self.messages[0]
        rest = self.messages[1:]
        return [
            head,
            {"role": "system", "content": self._turn_context},
            *rest,
        ]

    def _consume_stream(self, chunks):
        content = []
        thinking = []
        tool_calls = []
        for chunk in chunks:
            message = chunk.message
            think = getattr(message, "thinking", None) or ""
            piece = message.content or ""
            if think:
                thinking.append(think)
                if self.on_thinking:
                    self.on_thinking(think)
            if piece:
                content.append(piece)
                if self.on_token:
                    self.on_token(piece)
            if message.tool_calls:
                tool_calls.extend(message.tool_calls)
        return SimpleNamespace(
            role="assistant",
            content="".join(content) or None,
            thinking="".join(thinking) or None,
            tool_calls=tool_calls or None,
        )

    def _history_message(self, message):
        entry = {
            "role": getattr(message, "role", "assistant"),
            "content": message.content or "",
        }
        thinking = getattr(message, "thinking", None)
        if thinking:
            entry["thinking"] = thinking
        if message.tool_calls:
            dumped = []
            for call in message.tool_calls:
                if hasattr(call, "model_dump"):
                    dumped.append(call.model_dump())
                else:
                    dumped.append(call)
            entry["tool_calls"] = dumped
        return entry
