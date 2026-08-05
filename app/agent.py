"""Agent assembly and the graph entrypoint.

`langgraph.json` and the Dockerfile's LANGSERVE_GRAPHS both resolve
`app/agent.py:build_agent`. LangGraph accepts a factory, so nothing is built at
import time — the graph is constructed when the server asks for it.
"""

from __future__ import annotations

from dotenv import load_dotenv

# Loaded before app.config is imported, so module-level defaults see .env.
# The dev server also injects .env via langgraph.json; this covers direct runs.
load_dotenv(override=True)

from deepagents import create_deep_agent  # noqa: E402
from langchain.agents.middleware import TodoListMiddleware  # noqa: E402

from app import config  # noqa: E402
from app.backend import build_backend  # noqa: E402
from app.prompts import INSTRUCTIONS  # noqa: E402
from app.providers import register_provider_profiles  # noqa: E402
from app.tools import TOOLS  # noqa: E402


def build_agent():
    """Assemble the agent. This is the one place the pieces come together."""
    register_provider_profiles()

    return create_deep_agent(
        model=config.model_name(),
        tools=TOOLS,
        system_prompt=INSTRUCTIONS,
        # deepagents 0.7.0 dropped TodoListMiddleware from the defaults; pass it
        # explicitly to keep the write_todos planning tool.
        middleware=[TodoListMiddleware()],
        backend=build_backend(),
        # create_deep_agent wires SkillsMiddleware itself from this argument —
        # do not also pass that middleware above.
        skills=[config.SKILLS_PREFIX],
    )


if __name__ == "__main__":
    agent = build_agent()
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What are the latest LangChain releases?"}]},
        config={"configurable": {"thread_id": "1"}},
    )
    print(result["messages"][-1].content)
