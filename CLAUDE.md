# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install / update dependencies
uv run python -m app.agent     # run the agent directly
uv run langgraph dev           # start LangGraph Studio dev server
uv run pytest                  # run tests
langgraph deploy --name deep-agents-quick   # deploy to LangSmith Deployments
```

## Architecture

This is a [Deep Agents](https://docs.langchain.com/oss/python/deepagents/) application — an opinionated LangGraph-based agent harness with built-in middleware for filesystem context and subagent delegation. As of `deepagents` 0.7.0 task planning is *not* a default: `app/agent.py` passes `middleware=[TodoListMiddleware()]` explicitly to keep the `write_todos` tool.

```
app/
  agent.py            # build_agent() — graph entrypoint and the only wiring
  config.py           # every env var read, in one module
  prompts.py          # INSTRUCTIONS
  providers.py        # provider profile registration
  backend.py          # CompositeBackend: state + routed skills
  tools/
    __init__.py       # TOOLS registry
    search.py         # internet_search
    xlsx.py           # write_xlsx / read_xlsx
skills/
  xlsx-io/SKILL.md
tests/
```

**Module responsibilities:**

- `app/agent.py` — `build_agent()` assembles model, tools, skills, middleware, and backend. It is also the graph entrypoint: `langgraph.json` and `Dockerfile`'s `LANGSERVE_GRAPHS` both resolve `app/agent.py:build_agent`. **Change one and you must change the other.** LangGraph accepts a factory, so nothing is constructed at import time.
- `app/config.py` — all `os.getenv` calls live here; read at call time so tests can monkeypatch
- `app/tools/__init__.py` — the `TOOLS` list that `build_agent` passes through
- `app/tools/xlsx.py` — serializes and parses Office Open XML in-process via `openpyxl`
- `skills/xlsx-io/SKILL.md` — when to choose XLSX over CSV and how to shape sheets

**Adding a tool:** create a module in `app/tools/`, then add the callable to `TOOLS` in `app/tools/__init__.py`. Nothing else changes — `tests/test_agent.py` asserts every entry in `TOOLS` reaches the compiled graph, so a tool that fails to register fails the suite. Plain functions are fine; deepagents wraps them.

**Adding a skill:** create `skills/<name>/SKILL.md` with `name` and `description` frontmatter. No code change — `skills=[SKILLS_PREFIX]` loads the whole directory, and the tests assert each skill directory has a `SKILL.md` that resolves through the backend.

**Packaging:** `pyproject.toml` declares `packages` and `py-modules` explicitly. Do not remove them: with a package directory *and* a root-level module, setuptools flat-layout auto-discovery is ambiguous and the Docker `uv pip install -e .` fails.

**Spreadsheet I/O:**

An `.xlsx` is a ZIP of Office Open XML parts, so it is built in memory — no sandbox and no `execute`. That matters here because the agent's `execute` tool is inert: `StateBackend` does not implement `SandboxBackendProtocol`, so `execute` always returns an error.

Workbooks cannot live in the agent's virtual filesystem either — `StateBackend` stores files as text and base64-encodes binary, producing an unopenable blob. `app/tools/xlsx.py` therefore writes to the real filesystem under `XLSX_OUTPUT_DIR` and reads from `XLSX_INPUT_DIR` plus the output dir.

**Skills:**

`create_deep_agent(skills=[...])` wires `SkillsMiddleware` itself; do not pass that middleware by hand. Skills are read through the agent's own backend, so `app/backend.py` routes just the `/skills/` prefix to a `FilesystemBackend` via `CompositeBackend` and leaves scratch files ephemeral in `StateBackend`. Pointing the whole backend at disk would also grant the agent recursive `delete` over the repo. `CompositeBackend` strips the matched prefix before delegating, so that backend's `root_dir` is the `skills/` directory itself.

**Provider switching:**

Set `MODEL` in `.env` to switch providers:
- `MODEL=anthropic:claude-sonnet-5` (default)
- `MODEL=ollama:qwen3:27b` — requires Ollama running at `http://localhost:11434`

`ProviderProfile` init_kwargs supply provider-level defaults (e.g. `base_url` for Ollama). The model name must come from the model string itself, not from `init_kwargs`, to avoid a duplicate-argument error in `init_chat_model`.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | For Anthropic | |
| `TAVILY_API_KEY` | Always | Used by `internet_search` |
| `MODEL` | No | Defaults to `anthropic:claude-sonnet-5` |
| `OLLAMA_BASE_URL` | No | Defaults to `http://localhost:11434` |
| `XLSX_OUTPUT_DIR` | No | Where `write_xlsx` saves; defaults to `./output` |
| `XLSX_INPUT_DIR` | No | Where `read_xlsx` looks; defaults to `./input` |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | For tracing | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name; defaults to `deep-agents-quick` |
