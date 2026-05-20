import os

from dotenv import load_dotenv

load_dotenv(override=True)

import profiles  # registers anthropic and ollama provider profiles
from deepagents import create_deep_agent
from tools import internet_search


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
