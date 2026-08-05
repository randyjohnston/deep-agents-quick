from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from docx import Document as DocxDocument

from app.tools.office import paths
from app.tools.office.docx import Document, read_docx, write_docx
from app.tools.office.pptx import Deck, read_pptx, write_pptx
from app.tools.office.xlsx import Sheet, read_xlsx, write_xlsx


def _write_xlsx(name):
    return write_xlsx(name, [Sheet(name="S", rows=[["x"]])])


def _write_docx(name):
    return write_docx(name, Document(title="T"))


def _write_pptx(name):
    return write_pptx(name, Deck(title="T"))


WRITER_CASES = [
    pytest.param(_write_xlsx, ".xlsx", id="xlsx"),
    pytest.param(_write_docx, ".docx", id="docx"),
    pytest.param(_write_pptx, ".pptx", id="pptx"),
]
READER_CASES = [
    pytest.param(read_xlsx, ".xlsx", id="xlsx"),
    pytest.param(read_docx, ".docx", id="docx"),
    pytest.param(read_pptx, ".pptx", id="pptx"),
]


@pytest.mark.parametrize("writer,extension", WRITER_CASES)
def test_writers_add_extension_and_reject_escape(_isolate_dirs, writer, extension):
    writer("safe")
    assert (_isolate_dirs / "out" / f"safe{extension}").is_file()
    with pytest.raises(ValueError, match="directories"):
        writer(f"../escape{extension}")


@pytest.mark.parametrize("reader,extension", READER_CASES)
def test_readers_refuse_paths_outside_roots(_isolate_dirs, reader, extension):
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


@pytest.mark.parametrize("reader,extension", READER_CASES)
def test_readers_normalize_missing_office_parts(_isolate_dirs, reader, extension):
    plain_zip = _isolate_dirs / "in" / f"plain{extension}"
    with ZipFile(plain_zip, "w") as archive:
        archive.writestr("ordinary.txt", "not an Office package")

    with pytest.raises(ValueError, match="Not a valid Office Open XML"):
        reader(plain_zip.name)


@pytest.mark.parametrize(
    "writer,reader,extension,member",
    [
        pytest.param(
            _write_xlsx, read_xlsx, ".xlsx", "xl/workbook.xml", id="xlsx"
        ),
        pytest.param(
            _write_docx, read_docx, ".docx", "word/document.xml", id="docx"
        ),
        pytest.param(
            _write_pptx,
            read_pptx,
            ".pptx",
            "ppt/presentation.xml",
            id="pptx",
        ),
    ],
)
def test_readers_normalize_malformed_xml(_isolate_dirs, writer, reader, extension, member):
    writer("malformed")
    path = _isolate_dirs / "out" / f"malformed{extension}"
    _replace_member(path, member, b"<not valid XML")

    with pytest.raises(ValueError, match="Not a valid Office Open XML"):
        reader(path.name)


def _replace_member(path, target: str, replacement: bytes) -> None:
    buffer = BytesIO()
    with ZipFile(path) as source, ZipFile(buffer, "w") as destination:
        for member in source.infolist():
            destination.writestr(
                member,
                replacement if member.filename == target else source.read(member),
            )
    path.write_bytes(buffer.getvalue())
