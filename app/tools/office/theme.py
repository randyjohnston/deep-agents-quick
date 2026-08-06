"""Bounded Office theming with named JSON/TOML manifests."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import office_theme_dir
from app.tools.office.paths import resolve_image_path

MAX_THEME_BYTES = 64 * 1024
_THEME_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")


class Theme(BaseModel):
    """A bounded, reusable branding vocabulary for every Office writer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, description="Named theme in OFFICE_THEME_DIR")
    accent_color: str | None = Field(default=None, description="Six-digit RGB accent color")
    header_background: str | None = Field(
        default=None, description="Six-digit RGB header background color"
    )
    header_foreground: str | None = Field(
        default=None, description="Six-digit RGB header text color"
    )
    heading_font: str | None = Field(default=None, min_length=1, max_length=100)
    body_font: str | None = Field(default=None, min_length=1, max_length=100)
    logo: str | None = Field(
        default=None, min_length=1, max_length=255, description="PNG/JPEG under OFFICE_INPUT_DIR"
    )

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str | None) -> str | None:
        if value is not None and not _THEME_NAME.fullmatch(value):
            raise ValueError("theme name must contain only letters, digits, '-' and '_'")
        return value

    @field_validator("accent_color", "header_background", "header_foreground")
    @classmethod
    def _valid_color(cls, value: str | None) -> str | None:
        if value is not None and not _HEX_COLOR.fullmatch(value):
            raise ValueError("colors must be six hexadecimal RGB digits without '#'")
        return value.upper() if value else value


class ResolvedTheme(BaseModel):
    """Validated theme values plus a resolved logo path."""

    accent_color: str | None = None
    header_background: str | None = None
    header_foreground: str | None = None
    heading_font: str | None = None
    body_font: str | None = None
    logo: Path | None = None


def resolve_theme(theme: Theme | None) -> ResolvedTheme | None:
    """Resolve a named theme, apply explicit overrides, and validate its logo."""
    if theme is None:
        return None
    values: dict[str, object] = {}
    if theme.name:
        values.update(_load_named_theme(theme.name).model_dump(exclude_none=True, exclude={"name"}))
    for field in theme.model_fields_set - {"name"}:
        values[field] = getattr(theme, field)
    if logo := values.get("logo"):
        values["logo"] = resolve_image_path(str(logo))
    return ResolvedTheme.model_validate(values)


def _load_named_theme(name: str) -> Theme:
    root = office_theme_dir()
    candidates = [(root / f"{name}.json").resolve(), (root / f"{name}.toml").resolve()]
    found = [path for path in candidates if path.is_relative_to(root) and path.is_file()]
    if not found:
        raise FileNotFoundError(f"No named Office theme {name!r} in {root}")
    if len(found) > 1:
        raise ValueError(f"Theme {name!r} is ambiguous; keep only its JSON or TOML file")
    path = found[0]
    if path.stat().st_size > MAX_THEME_BYTES:
        raise ValueError(f"Theme {name!r} exceeds the {MAX_THEME_BYTES}-byte limit")
    try:
        with path.open("rb") as source:
            data = json.load(source) if path.suffix == ".json" else tomllib.load(source)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Theme {name!r} is not valid {path.suffix[1:].upper()}") from exc
    loaded = Theme.model_validate(data)
    if loaded.name:
        raise ValueError("Named theme files cannot reference another named theme")
    return loaded
