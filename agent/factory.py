from agent.agent import Agent
from agent.prompt import MODEL, SYSTEM_PROMPT


def create_agent(confirm=None, on_tool=None):
    return Agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        confirm=confirm,
        on_tool=on_tool,
    )
