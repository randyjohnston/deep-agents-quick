"""Environment-derived settings, resolved in one place.

Every module reads configuration from here rather than calling os.getenv
directly, so the full set of knobs is greppable and testable.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root: app/config.py -> app/ -> repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL = "anthropic:claude-sonnet-5"

# Virtual path prefix the agent uses to reach skills; see app/backend.py.
SKILLS_PREFIX = "/skills/"

# Skills live at the repo root so they are editable without touching the
# package, and the Docker build installs the repo with `-e .` so they stay
# on disk at this path inside the image.
SKILLS_DIR = REPO_ROOT / "skills"


def model_name() -> str:
    return os.getenv("MODEL", DEFAULT_MODEL)


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def xlsx_output_dir() -> Path:
    """Where write_xlsx saves. Read at call time so tests can monkeypatch it."""
    return Path(os.getenv("XLSX_OUTPUT_DIR", "output")).expanduser().resolve()


def xlsx_input_dirs() -> list[Path]:
    """Roots read_xlsx may read from: the input dir, plus anything we wrote."""
    roots = [Path(os.getenv("XLSX_INPUT_DIR", "input")).expanduser().resolve()]
    if (out := xlsx_output_dir()) not in roots:
        roots.append(out)
    return roots
