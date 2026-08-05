"""Wiring tests: the structure holds together without calling a model."""

from __future__ import annotations

import json
import re

import pytest

from app import config
from app.agent import build_agent
from app.backend import build_backend
from app.tools import TOOLS

GRAPH_ENTRYPOINT = "app/agent.py:build_agent"


@pytest.fixture(scope="module")
def graph():
    return build_agent()


def _tool_names(graph) -> set[str]:
    node = graph.nodes["tools"]
    node = node.bound if hasattr(node, "bound") else node
    return set(node.tools_by_name)


def test_registry_tools_all_reach_the_agent(graph):
    registered = _tool_names(graph)
    for tool in TOOLS:
        assert tool.__name__ in registered, f"{tool.__name__} is in TOOLS but not on the graph"


def test_builtin_filesystem_and_planning_tools_are_present(graph):
    names = _tool_names(graph)
    # write_todos only exists because TodoListMiddleware is passed explicitly;
    # deepagents 0.7.0 dropped it from the defaults.
    assert "write_todos" in names
    assert {"ls", "read_file", "write_file", "edit_file"} <= names


def test_skills_middleware_is_wired_from_the_skills_argument(graph):
    assert any(n.startswith("SkillsMiddleware") for n in graph.nodes), sorted(graph.nodes)


def test_skill_files_resolve_through_the_routed_backend():
    backend = build_backend()
    for skill_dir in sorted(p for p in config.SKILLS_DIR.iterdir() if p.is_dir()):
        virtual = f"{config.SKILLS_PREFIX}{skill_dir.name}/SKILL.md"
        result = backend.read(virtual)
        assert not getattr(result, "error", None), f"{virtual}: {result.error}"


def test_every_skill_dir_has_a_skill_file():
    skill_dirs = [p for p in config.SKILLS_DIR.iterdir() if p.is_dir()]
    assert skill_dirs, f"no skills found under {config.SKILLS_DIR}"
    for d in skill_dirs:
        assert (d / "SKILL.md").is_file(), f"{d.name} is missing SKILL.md"


def test_langgraph_json_and_dockerfile_agree_on_the_entrypoint():
    """These two drift silently and only break at deploy time."""
    graphs = json.loads((config.REPO_ROOT / "langgraph.json").read_text())["graphs"]
    assert graphs["agent"].endswith(GRAPH_ENTRYPOINT), graphs

    dockerfile = (config.REPO_ROOT / "Dockerfile").read_text()
    declared = re.search(r"LANGSERVE_GRAPHS='([^']+)'", dockerfile)
    assert declared, "LANGSERVE_GRAPHS not found in Dockerfile"
    assert json.loads(declared.group(1))["agent"].endswith(GRAPH_ENTRYPOINT)


def test_search_tool_import_does_not_require_an_api_key(monkeypatch):
    # The client is built lazily, so importing must work with no key present.
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    from app.tools.search import _client, internet_search

    _client.cache_clear()
    assert callable(internet_search)
    with pytest.raises(RuntimeError, match="TAVILY_API_KEY is not set"):
        _client()
    _client.cache_clear()
