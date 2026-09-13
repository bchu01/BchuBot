from ollama import chat


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

        response = chat(
            model=self.model,
            messages=self.messages
        )

        assistant_message = response.message.content

        self.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message