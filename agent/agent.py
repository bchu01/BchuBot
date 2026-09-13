import json

from ollama import chat
from tools.registry import TOOL_REGISTRY, TOOL_DEFINITIONS


class Agent:
    def __init__(self, model, system_prompt):
        self.model = model
        self.system_prompt = system_prompt

        self.messages = [
            {
                "role": "system",
                "content": self.system_prompt
            }
        ]

    def chat(self, user_input):
        self.messages.append({
            "role": "user",
            "content": user_input
        })

        while True:
            response = chat(
                model=self.model,
                messages=self.messages,
                tools=TOOL_DEFINITIONS
            )

            if not response.message.tool_calls:
                assistant_message = response.message.content

                self.messages.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                return assistant_message

            self.messages.append(response.message)

            for tool_call in response.message.tool_calls:
                tool_name = tool_call.function.name

                if tool_name not in TOOL_REGISTRY:
                    tool_result = f"Unknown tool: {tool_name}"

                else:
                    tool = TOOL_REGISTRY[tool_name]

                    arguments = tool_call.function.arguments

                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)

                    try:
                        tool_result = tool(**arguments)
                    except Exception as e:
                        tool_result = f"Tool error: {str(e)}"

                self.messages.append({
                    "role": "tool",
                    "content": str(tool_result)
                })