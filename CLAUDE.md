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
    office/
      __init__.py     # OFFICE_TOOLS registry
      paths.py        # shared path confinement and OOXML size checks
      theme.py        # bounded named/inline branding and logo validation
      xlsx.py         # write_xlsx / read_xlsx
      docx.py         # write_docx / read_docx
      pptx.py         # write_pptx / read_pptx
skills/
  xlsx-io/SKILL.md
  docx-io/SKILL.md
  pptx-io/SKILL.md
tests/
```

**Module responsibilities:**

- `app/agent.py` — `build_agent()` assembles model, tools, skills, middleware, and backend. It is also the graph entrypoint: `langgraph.json` and `Dockerfile`'s `LANGSERVE_GRAPHS` both resolve `app/agent.py:build_agent`. **Change one and you must change the other.** LangGraph accepts a factory, so nothing is constructed at import time.
- `app/config.py` — all `os.getenv` calls live here; read at call time so tests can monkeypatch
- `app/tools/__init__.py` — the `TOOLS` list that `build_agent` passes through
- `app/tools/office/` — typed Office Open XML tools plus shared filesystem and archive policy
- `skills/*-io/SKILL.md` — when to choose each Office format and how to shape its content

**Adding a tool:** create a module in `app/tools/`, then add the callable to `TOOLS` in `app/tools/__init__.py`. Office formats instead go in `app/tools/office/` and register through `OFFICE_TOOLS`. `tests/test_agent.py` asserts every entry in `TOOLS` reaches the compiled graph. Plain functions are fine; deepagents wraps them.

**Adding a skill:** create `skills/<name>/SKILL.md` with `name` and `description` frontmatter. No code change — `skills=[SKILLS_PREFIX]` loads the whole directory, and the tests assert each skill directory has a `SKILL.md` that resolves through the backend.

**Packaging:** `pyproject.toml` declares packages explicitly. Keep `app.tools.office` in that list or the Docker editable install silently omits the Office subpackage.

**Office file I/O:**

XLSX, DOCX, and PPTX files are ZIPs of Office Open XML parts, so they are built in-process — no sandbox and no `execute`. That matters here because the agent's `execute` tool is inert: `StateBackend` does not implement `SandboxBackendProtocol`, so `execute` always returns an error.

Office files cannot live in the agent's virtual filesystem either — `StateBackend` stores files as text and base64-encodes binary, producing an unopenable blob. `app/tools/office/` therefore writes to the real filesystem under `OFFICE_OUTPUT_DIR` and reads from `OFFICE_INPUT_DIR` plus the output dir. The older `XLSX_*` variables remain fallbacks.

Each writer accepts a bounded `Theme` plus a guarded native template (`.xltx`, `.dotx`, or `.potx`). Named JSON/TOML themes resolve under `OFFICE_THEME_DIR`; logos and templates remain confined to Office input roots. Do not add raw OOXML fields or a local script runner. If arbitrary generated layout becomes necessary, use a backend implementing `SandboxBackendProtocol` such as `LangSmithSandbox`; `LocalShellBackend` is explicitly unsuitable for untrusted model-generated code.

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
| `OFFICE_OUTPUT_DIR` | No | Where Office writers save; defaults to `./output` |
| `OFFICE_INPUT_DIR` | No | Where Office readers look; defaults to `./input` |
| `OFFICE_THEME_DIR` | No | Where named JSON/TOML themes live; defaults to `./themes` |
| `XLSX_OUTPUT_DIR` | No | Legacy fallback for `OFFICE_OUTPUT_DIR` |
| `XLSX_INPUT_DIR` | No | Legacy fallback for `OFFICE_INPUT_DIR` |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | For tracing | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name; defaults to `deep-agents-quick` |
