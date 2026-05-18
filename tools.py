import os
from typing import Literal

from tavily import TavilyClient


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return TavilyClient(os.environ["TAVILY_API_KEY"]).search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
