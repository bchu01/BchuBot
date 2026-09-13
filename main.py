from ollama import chat

response = chat(
    model="qwen3:8b",
    messages=[
        {
            "role": "user",
            "content": "Hello! Introduce yourself as BchuBot."
        }
    ]
)

print(response.message.content)