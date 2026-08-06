"""Shared path confinement and ZIP-bomb checks for Office Open XML files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import TypeVar
from xml.etree.ElementTree import ParseError
from zlib import error as ZlibError
from zipfile import BadZipFile, ZipFile

from lxml.etree import XMLSyntaxError

from app.config import office_input_dirs, office_output_dir

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 200 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 10_000
MAX_IMAGE_PIXELS = 25_000_000
_MACRO_EXTENSIONS = {".docm", ".dotm", ".pptm", ".potm", ".xlsm", ".xltm"}
_IMAGE_EXTENSIONS = {".jpeg", ".jpg", ".png"}
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


def resolve_template_path(path_or_name: str, extensions: tuple[str, ...]) -> Path:
    """Resolve a non-macro Office template through the normal archive guard."""
    if Path(path_or_name).suffix.lower() in _MACRO_EXTENSIONS:
        raise ValueError(f"Macro-enabled Office templates are not supported: {path_or_name!r}")
    path = resolve_read_path(path_or_name, extensions)
    _reject_embedded_macros(path)
    return path


def _reject_embedded_macros(path: Path) -> None:
    """Reject macro content even when a package was renamed to a safe extension."""
    try:
        with ZipFile(path) as archive:
            names = {member.filename.casefold() for member in archive.infolist()}
            if any(name.endswith("vbaproject.bin") for name in names):
                raise ValueError(f"Macro content is not supported in template {path.name!r}")
            if "[content_types].xml" in names:
                content_types = archive.read("[Content_Types].xml").lower()
                if b"macroenabled" in content_types or b"vbaproject" in content_types:
                    raise ValueError(f"Macro content is not supported in template {path.name!r}")
    except (BadZipFile, ZlibError, KeyError) as exc:
        raise ValueError(f"Not a valid Office template: {path.name!r}") from exc


def resolve_image_path(path_or_name: str) -> Path:
    """Resolve and validate a bounded PNG/JPEG asset under an Office input root."""
    from PIL import Image, UnidentifiedImageError

    path = _resolve_permitted_file(path_or_name)
    if path.suffix.lower() not in _IMAGE_EXTENSIONS:
        raise ValueError(f"Expected a PNG or JPEG logo; got {path.name!r}")
    size = path.stat().st_size
    if size > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Refusing {path.name!r}: image is {size} bytes; limit is {MAX_IMAGE_BYTES}."
        )
    try:
        with Image.open(path) as image:
            width, height = image.size
            if (
                width <= 0
                or height <= 0
                or max(width, height) > MAX_IMAGE_DIMENSION
                or width * height > MAX_IMAGE_PIXELS
            ):
                raise ValueError(
                    f"Refusing {path.name!r}: image is {width}x{height}; "
                    f"limits are {MAX_IMAGE_DIMENSION}px per side and {MAX_IMAGE_PIXELS} pixels."
                )
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Not a valid PNG or JPEG image: {path.name!r}") from exc
    return path


def _resolve_permitted_file(path_or_name: str) -> Path:
    """Resolve an existing file under one of the shared Office input roots."""
    candidate = Path(path_or_name).expanduser()
    roots = office_input_dirs()
    if candidate.is_absolute():
        resolved = candidate.resolve()
        if any(resolved.is_relative_to(root) for root in roots) and resolved.is_file():
            return resolved
    else:
        for root in roots:
            resolved = (root / candidate).resolve()
            if resolved.is_relative_to(root) and resolved.is_file():
                return resolved
    raise FileNotFoundError(f"No permitted Office asset found for {path_or_name!r}")


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


def load_office_template(
    path: Path,
    loader: Callable[[object], T],
    template_content_type: str,
    document_content_type: str,
) -> T:
    """Load a guarded template as its non-template output package type."""
    try:
        with SpooledTemporaryFile(max_size=10 * 1024 * 1024) as converted:
            with ZipFile(path) as source, ZipFile(converted, "w") as destination:
                for member in source.infolist():
                    payload = source.read(member)
                    if member.filename == "[Content_Types].xml":
                        payload = payload.replace(
                            template_content_type.encode(), document_content_type.encode()
                        )
                    destination.writestr(member, payload)
            converted.seek(0)
            return loader(converted)
    except (BadZipFile, ZlibError, KeyError, ParseError, XMLSyntaxError, ValueError) as exc:
        raise ValueError(f"Not a valid Office template: {path.name!r}") from exc
