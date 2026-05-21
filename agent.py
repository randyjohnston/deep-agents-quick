import os
from typing import Literal

from dotenv import load_dotenv
from tavily import TavilyClient
from deepagents import ProviderProfile, create_deep_agent, register_provider_profile

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
"""

agent = create_deep_agent(
    model=os.getenv("MODEL", "anthropic:claude-sonnet-4-6"),
    tools=[internet_search],
    system_prompt=INSTRUCTIONS,
)

if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What are the latest LangChain releases?"}]},
        config={"configurable": {"thread_id": "1"}},
    )
    print(result["messages"][-1].content)
