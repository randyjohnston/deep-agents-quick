from __future__ import annotations

from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from docx import Document as DocxDocument

from app.tools.office import paths
from app.tools.office.docx import Document, read_docx, write_docx
from app.tools.office.pptx import Deck, read_pptx, write_pptx
from app.tools.office.xlsx import Sheet, read_xlsx, write_xlsx


FORMAT_CASES = [
    pytest.param(
        lambda name: write_xlsx(name, [Sheet(name="S", rows=[["x"]])]),
        read_xlsx,
        ".xlsx",
        id="xlsx",
    ),
    pytest.param(
        lambda name: write_docx(name, Document(title="T")),
        read_docx,
        ".docx",
        id="docx",
    ),
    pytest.param(
        lambda name: write_pptx(name, Deck(title="T")),
        read_pptx,
        ".pptx",
        id="pptx",
    ),
]


@pytest.mark.parametrize("writer,reader,extension", FORMAT_CASES)
def test_writers_add_extension_and_reject_escape(_isolate_dirs, writer, reader, extension):
    writer("safe")
    assert (_isolate_dirs / "out" / f"safe{extension}").is_file()
    with pytest.raises(ValueError, match="directories"):
        writer(f"../escape{extension}")


@pytest.mark.parametrize("writer,reader,extension", FORMAT_CASES)
def test_readers_refuse_paths_outside_roots(_isolate_dirs, writer, reader, extension):
    outside = _isolate_dirs / f"outside{extension}"
    outside.write_bytes(b"not opened")
    with pytest.raises(FileNotFoundError):
        reader(str(outside))


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


def test_reader_normalizes_corrupt_member_error(_isolate_dirs):
    corrupt = _isolate_dirs / "in" / "corrupt.docx"
    DocxDocument().save(corrupt)
    with ZipFile(corrupt) as archive:
        member = archive.getinfo("word/document.xml")
        payload_offset = member.header_offset + 30 + len(member.filename.encode()) + len(member.extra)
    data = bytearray(corrupt.read_bytes())
    data[payload_offset] ^= 0xFF
    corrupt.write_bytes(data)

    with pytest.raises(ValueError, match="Not a valid Office Open XML"):
        read_docx("corrupt.docx")
