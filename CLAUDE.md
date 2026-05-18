# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install / update dependencies
uv run python main.py          # run the agent directly
uv run langgraph dev           # start LangGraph Studio dev server
```

## Architecture

This is a [Deep Agents](https://docs.langchain.com/oss/python/deepagents/) application — an opinionated LangGraph-based agent harness with built-in middleware for task planning, filesystem context, and subagent delegation.

**Module responsibilities:**

- `profiles.py` — registers `ProviderProfile` entries for `anthropic` and `ollama` at import time; must be imported before `create_deep_agent` is called
- `agent.py` — imports `profiles`, creates the agent via `create_deep_agent`, exports it as `agent`; model is selected via the `MODEL` env var (default `anthropic:claude-sonnet-4-6`)
- `tools.py` — defines `internet_search` using Tavily; client is instantiated lazily inside the function so `TAVILY_API_KEY` is read after `load_dotenv()` runs
- `main.py` — calls `load_dotenv()` then invokes `agent`; the only entry point that triggers `.env` loading
- `langgraph.json` — points the LangGraph dev server at `agent.py:graph`

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
