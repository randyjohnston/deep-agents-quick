"""Shared path confinement and ZIP-bomb checks for Office Open XML files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar
from xml.etree.ElementTree import ParseError
from zlib import error as ZlibError
from zipfile import BadZipFile, ZipFile

from lxml.etree import XMLSyntaxError

from app.config import office_input_dirs, office_output_dir

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 200 * 1024 * 1024
_MACRO_EXTENSIONS = {".docm", ".pptm", ".xlsm"}
T = TypeVar("T")


def resolve_write_path(filename: str, extension: str) -> Path:
    """Confine a basename to the output root and enforce one exact extension."""
    raw = filename.strip()
    name = Path(raw).name
    if not name or name in {".", ".."}:
        raise ValueError(f"Invalid filename: {filename!r}")
    if name != raw or "/" in raw or "\\" in raw:
        raise ValueError(f"Refusing a filename with directories: {filename!r}")
    if name.lower().endswith(tuple(_MACRO_EXTENSIONS)):
        raise ValueError(f"Macro-enabled Office output is not supported: {filename!r}")
    if not name.lower().endswith(extension):
        name = f"{name}{extension}"
    root = office_output_dir()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Refusing to write outside {root}: {filename!r}")
    return path


def resolve_read_path(path_or_name: str, extensions: tuple[str, ...]) -> Path:
    """Resolve inside permitted roots, verify the type, then inspect ZIP sizes."""
    candidate = Path(path_or_name).expanduser()
    roots = office_input_dirs()
    tried: list[Path] = []
    path: Path | None = None
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if any(resolved.is_relative_to(root) for root in roots) and resolved.is_file():
            path = resolved
        else:
            tried.append(resolved)
    else:
        for root in roots:
            resolved = (root / candidate).resolve()
            if not resolved.is_relative_to(root):
                continue
            if resolved.is_file():
                path = resolved
                break
            tried.append(resolved)
    if path is None:
        searched = ", ".join(str(item) for item in tried) or ", ".join(map(str, roots))
        raise FileNotFoundError(f"No Office file found for {path_or_name!r}. Looked in: {searched}")
    if path.suffix.lower() not in extensions:
        allowed = ", ".join(extensions)
        raise ValueError(f"Expected one of {allowed}; got {path.name!r}")
    validate_archive_size(path)
    return path


def validate_archive_size(path: Path) -> None:
    """Reject large or highly expanded OOXML packages before library parsing."""
    compressed = path.stat().st_size
    if compressed > MAX_ARCHIVE_BYTES:
        raise ValueError(
            f"Refusing {path.name!r}: archive is {compressed} bytes; limit is {MAX_ARCHIVE_BYTES}."
        )
    try:
        with ZipFile(path) as archive:
            expanded = sum(member.file_size for member in archive.infolist())
    except (BadZipFile, ZlibError) as exc:
        raise ValueError(f"Not a valid Office Open XML file: {path.name!r}") from exc
    if expanded > MAX_EXPANDED_BYTES:
        raise ValueError(
            f"Refusing {path.name!r}: expanded archive is {expanded} bytes; "
            f"limit is {MAX_EXPANDED_BYTES}."
        )


def load_office_file(path: Path, loader: Callable[[Path], T]) -> T:
    """Normalize corrupt-member failures raised after the initial ZIP check."""
    try:
        return loader(path)
    except (BadZipFile, ZlibError, KeyError, ParseError, XMLSyntaxError) as exc:
        raise ValueError(f"Not a valid Office Open XML file: {path.name!r}") from exc
