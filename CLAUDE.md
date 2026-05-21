# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install / update dependencies
uv run python agent.py         # run the agent directly
uv run langgraph dev           # start LangGraph Studio dev server
```

## Architecture

This is a [Deep Agents](https://docs.langchain.com/oss/python/deepagents/) application — an opinionated LangGraph-based agent harness with built-in middleware for task planning, filesystem context, and subagent delegation.

**Module responsibilities:**

- `agent.py` — registers provider profiles, defines `internet_search`, creates the agent, and (when run directly) invokes it; model is selected via the `MODEL` env var (default `anthropic:claude-sonnet-4-6`)
- `langgraph.json` — points the LangGraph dev server at `agent.py:agent`

**Provider switching:**

Set `MODEL` in `.env` to switch providers:
- `MODEL=anthropic:claude-sonnet-4-6` (default)
- `MODEL=ollama:qwen3:27b` — requires Ollama running at `http://localhost:11434`

`ProviderProfile` init_kwargs supply provider-level defaults (e.g. `base_url` for Ollama). The model name must come from the model string itself, not from `init_kwargs`, to avoid a duplicate-argument error in `init_chat_model`.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | For Anthropic | |
| `TAVILY_API_KEY` | Always | Used by `internet_search` |
| `MODEL` | No | Defaults to `anthropic:claude-sonnet-4-6` |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | For tracing | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name; defaults to `deep-agents-quick` |
