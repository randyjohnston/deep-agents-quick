"""Web search tool, backed by Tavily."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from tavily import TavilyClient


@lru_cache(maxsize=1)
def _client() -> TavilyClient:
    """Built on first use, not at import.

    Constructing this at module scope would make importing the package fail
    whenever TAVILY_API_KEY is unset — including in tests that never search.
    """
    try:
        api_key = os.environ["TAVILY_API_KEY"]
    except KeyError:
        raise RuntimeError(
            "TAVILY_API_KEY is not set; internet_search cannot run. "
            "Add it to .env (see .env.example)."
        ) from None
    return TavilyClient(api_key=api_key)


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return _client().search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
