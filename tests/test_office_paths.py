from __future__ import annotations

from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.tools.office import paths


def test_read_rejects_expanded_archive_over_limit(_isolate_dirs, monkeypatch):
    archive = _isolate_dirs / "in" / "bomb.docx"
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        output.writestr("word/document.xml", b"x" * 10_000)
    monkeypatch.setattr(paths, "MAX_EXPANDED_BYTES", 1_000)
    with pytest.raises(ValueError, match="expanded archive"):
        paths.resolve_read_path("bomb.docx", (".docx",))


def test_read_rejects_compressed_archive_over_limit(_isolate_dirs, monkeypatch):
    archive = _isolate_dirs / "in" / "large.pptx"
    with ZipFile(archive, "w") as output:
        output.writestr("ppt/presentation.xml", b"content")
    monkeypatch.setattr(paths, "MAX_ARCHIVE_BYTES", 1)
    with pytest.raises(ValueError, match="archive is"):
        paths.resolve_read_path("large.pptx", (".pptx",))


def test_read_rejects_invalid_zip(_isolate_dirs):
    invalid = _isolate_dirs / "in" / "invalid.xlsx"
    invalid.write_text("not a zip")
    with pytest.raises(ValueError, match="Not a valid"):
        paths.resolve_read_path("invalid.xlsx", (".xlsx",))
