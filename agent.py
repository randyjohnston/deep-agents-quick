import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from tavily import TavilyClient
from deepagents import ProviderProfile, create_deep_agent, register_provider_profile
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langchain.agents.middleware import TodoListMiddleware

from xlsx import read_xlsx, write_xlsx

load_dotenv(override=True)

register_provider_profile("anthropic", ProviderProfile())
register_provider_profile(
    "ollama",
    ProviderProfile(init_kwargs={"base_url": "http://localhost:11434"}),
)

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )


INSTRUCTIONS = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.

## Spreadsheet output

When the user wants Excel/XLSX output, multiple tabs, or types that survive the
round trip, use `write_xlsx` rather than emitting CSV. Read the `xlsx-io` skill
for the conventions before building a workbook.
"""

SKILLS_PREFIX = "/skills/"

# Skills load from disk, but the agent's own scratch files stay ephemeral: route
# only the skills prefix to the real filesystem. Pointing the whole backend at
# disk would also hand the agent recursive `delete` over this repo.
# CompositeBackend strips the matched prefix, so root_dir is the skills dir
# itself — a read of /skills/x/SKILL.md arrives here as /x/SKILL.md.
backend = CompositeBackend(
    default=StateBackend(),
    routes={SKILLS_PREFIX: FilesystemBackend(root_dir=Path(__file__).parent / "skills")},
)

agent = create_deep_agent(
    model=os.getenv("MODEL", "anthropic:claude-sonnet-5"),
    tools=[internet_search, write_xlsx, read_xlsx],
    system_prompt=INSTRUCTIONS,
    # deepagents 0.7.0 dropped TodoListMiddleware from the defaults; pass it
    # explicitly to keep the write_todos planning tool.
    middleware=[TodoListMiddleware()],
    backend=backend,
    skills=[SKILLS_PREFIX],
)

if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What are the latest LangChain releases?"}]},
        config={"configurable": {"thread_id": "1"}},
    )
    print(result["messages"][-1].content)
