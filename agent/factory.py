from agent.agent import Agent
from agent.prompt import MODEL, SYSTEM_PROMPT
from tools.memory import memories_for_prompt


def create_agent(
    confirm=None,
    on_tool=None,
    on_token=None,
    on_thinking=None,
    on_context=None,
):
    return Agent(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        confirm=confirm,
        on_tool=on_tool,
        on_token=on_token,
        on_thinking=on_thinking,
        context_for_message=memories_for_prompt,
        on_context=on_context,
    )
