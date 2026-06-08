import logging
import os
from typing import Literal

from dotenv import load_dotenv
from langchain.agents.middleware import PIIMiddleware
from langsmith import Client
from tavily import TavilyClient
from deepagents import ProviderProfile, create_deep_agent, register_provider_profile

from app.guardrails import policy_moderation_middleware

load_dotenv(override=True)

logger = logging.getLogger(__name__)

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


FALLBACK_INSTRUCTIONS = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
"""


def load_instructions() -> str:
    """Pull system prompt from LangSmith Context Hub, falling back to inline copy."""
    ref = os.getenv("LANGSMITH_CONTEXT_REF", "default/deep-agents-quick")
    try:
        ctx = Client().pull_agent(ref)
        return ctx.files["AGENTS.md"].content
    except Exception as exc:
        logger.warning("Context Hub pull failed for %r (%s); using inline fallback.", ref, exc)
        return FALLBACK_INSTRUCTIONS


middleware = []

# ── Threat detection: Cisco AI Defense (optional) ─────────────────────────────
# Requires: uv sync --extra cisco + CISCO_AI_DEFENSE_API_KEY in .env
#
# try:
#     from aidefense_langchain import AIDefenseMiddleware
#     middleware.append(AIDefenseMiddleware(
#         api_key=os.getenv("CISCO_AI_DEFENSE_API_KEY", ""),
#         region=os.getenv("CISCO_AI_DEFENSE_REGION", "us-west-2"),
#         mode="monitor",  # switch to "enforce" when ready to block
#     ))
# except ImportError:
#     logger.warning("Cisco AI Defense not installed; run: uv sync --extra cisco")

# ── PII Redaction (OOTB, no extra packages) ───────────────────────────────────
middleware += [
    PIIMiddleware("email", strategy="redact", apply_to_input=True, apply_to_output=True),
    PIIMiddleware("credit_card", strategy="redact", apply_to_input=True, apply_to_output=True),
    PIIMiddleware("ip", strategy="redact", apply_to_input=True, apply_to_output=True),
    PIIMiddleware("ssn", detector=r"\b\d{3}-\d{2}-\d{4}\b",
                  strategy="block", apply_to_tool_results=True)
]

# ── Policy Content Moderation (before_agent input + after_agent output rails) ─
middleware += policy_moderation_middleware(block_on_violation=True)

agent = create_deep_agent(
    model=os.getenv("MODEL", "anthropic:claude-sonnet-4-6"),
    tools=[internet_search],
    system_prompt=load_instructions(),
    middleware=middleware,
)

if __name__ == "__main__":
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What are the latest LangChain releases?"}]},
        config={"configurable": {"thread_id": "1"}},
    )
    print(result["messages"][-1].content)
