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


def office_output_dir() -> Path:
    """Where Office writers save, with the old XLSX setting as a fallback."""
    value = os.getenv("OFFICE_OUTPUT_DIR") or os.getenv("XLSX_OUTPUT_DIR", "output")
    return Path(value).expanduser().resolve()


def office_input_dirs() -> list[Path]:
    """Roots Office readers may use, including the shared output directory."""
    value = os.getenv("OFFICE_INPUT_DIR") or os.getenv("XLSX_INPUT_DIR", "input")
    roots = [Path(value).expanduser().resolve()]
    if (out := office_output_dir()) not in roots:
        roots.append(out)
    return roots


def office_theme_dir() -> Path:
    """Directory containing named JSON or TOML Office themes."""
    return Path(os.getenv("OFFICE_THEME_DIR", "themes")).expanduser().resolve()


def office_image_domains() -> frozenset[str]:
    """Optional comma-separated hostname boundary for remote Office images."""
    value = os.getenv("OFFICE_IMAGE_DOMAINS", "")
    return frozenset(
        part.strip().casefold().rstrip(".") for part in value.split(",") if part.strip()
    )
