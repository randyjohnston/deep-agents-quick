# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install / update dependencies
uv run python agent.py         # run the agent directly
uv run langgraph dev           # start LangGraph Studio dev server
uv run python scripts/push_context.py       # publish system prompt to LangSmith Context Hub
langgraph deploy --name deep-agents-quick   # deploy to LangSmith Deployments
```

## Architecture

This is a [Deep Agents](https://docs.langchain.com/oss/python/deepagents/) application — an opinionated LangGraph-based agent harness with built-in middleware for task planning, filesystem context, and subagent delegation.

**Module responsibilities:**

- `agent.py` — registers provider profiles, defines `internet_search`, creates the agent, and (when run directly) invokes it; model is selected via the `MODEL` env var (default `anthropic:claude-sonnet-4-6`)
- `langgraph.json` — points the LangGraph dev server at `agent.py:agent`
- `scripts/push_context.py` — pushes the inline `FALLBACK_INSTRUCTIONS` to the LangSmith Context Hub agent named `deep-agents-quick-researcher`

**System prompt loading:**

At import time, `agent.py` calls `Client().pull_agent(LANGSMITH_CONTEXT_REF or "deep-agents-quick-researcher")` and uses `AGENTS.md` as the system prompt. If the pull fails (no key, offline, missing repo), it falls back to the inline `FALLBACK_INSTRUCTIONS` string and logs a warning — local dev keeps working without LangSmith. Pin to a tag in deployment via `LANGSMITH_CONTEXT_REF=deep-agents-quick-researcher:production`.

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
| `LANGSMITH_API_KEY` | For Context Hub | Required to pull/push agent contexts |
| `LANGSMITH_CONTEXT_REF` | No | Context Hub ref (e.g. `deep-agents-quick-researcher:production`); defaults to `deep-agents-quick-researcher` |
