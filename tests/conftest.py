"""Shared test isolation for all filesystem-backed Office tools."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OFFICE_OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("OFFICE_INPUT_DIR", str(tmp_path / "in"))
    (tmp_path / "in").mkdir()
    return tmp_path
