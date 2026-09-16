from agent.factory import create_agent
from tools.alarms import add_alarm_listener, fired_message, start_scheduler, stop_scheduler


print("BchuBot is online.")
print("Type 'exit' to quit.\n")


def on_alarm(item):
    print(f"\nBchuBot: {fired_message(item)}\n")


add_alarm_listener(on_alarm)
start_scheduler()
bchubot = create_agent()

try:
    while True:
        user_input = input("You: ")

        if user_input.lower() == "exit":
            print("BchuBot: Goodbye!")
            break

        response = bchubot.chat(user_input)

        print(f"BchuBot: {response}\n")
finally:
    stop_scheduler()
