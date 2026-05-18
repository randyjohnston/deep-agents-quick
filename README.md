# Deep Agents Quick Start

A research agent built on [Deep Agents](https://docs.langchain.com/oss/python/deepagents/) (LangGraph) that searches the web and writes polished reports. Supports Anthropic and Ollama providers via profile-based configuration.

## Setup

```bash
uv sync
cp .env.example .env  # then fill in your keys
uv run python main.py
```

## Environment variables

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | For Anthropic | Your Anthropic API key |
| `TAVILY_API_KEY` | Always | Web search API key ([tavily.com](https://tavily.com)) |
| `MODEL` | No | Model string — see below |

## Switching model providers

The `MODEL` environment variable selects the provider and model. Two providers are pre-configured:

**Anthropic** (default):
```
MODEL=anthropic:claude-sonnet-4-6
```

**Ollama** (local):
```
MODEL=ollama:qwen3:27b
```

Ollama must be running locally (`ollama serve`) with the model pulled:
```bash
ollama pull qwen3:27b
```

To add a new provider, register a `ProviderProfile` in `profiles.py` and set `MODEL=<provider>:<model>`.
