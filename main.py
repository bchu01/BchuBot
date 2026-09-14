from agent.factory import create_agent


print("BchuBot is online.")
print("Type 'exit' to quit.\n")


bchubot = create_agent()

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("BchuBot: Goodbye!")
        break

    response = bchubot.chat(user_input)

    print(f"BchuBot: {response}\n")
