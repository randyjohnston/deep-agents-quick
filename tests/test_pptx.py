from __future__ import annotations

import pytest
from pptx import Presentation

from app.tools.office.pptx import Deck, Slide, read_pptx, write_pptx


def test_pptx_round_trip_with_title_and_bullets(_isolate_dirs):
    result = write_pptx(
        "deck",
        Deck(title="Quarterly Review", subtitle="Q3", slides=[Slide(title="Growth", bullets=["18% YoY"])]),
    )
    path = _isolate_dirs / "out" / "deck.pptx"
    assert path.is_file(), result
    parsed = Presentation(path)
    assert len(parsed.slides) == 2
    assert parsed.slides[1].shapes.title.text == "Growth"
    assert "18% YoY" in read_pptx("deck.pptx")


def test_pptx_rejects_empty_content(_isolate_dirs):
    with pytest.raises(ValueError, match="Provide"):
        write_pptx("empty", Deck())


def test_pptx_rejects_escape_and_macro_extension(_isolate_dirs):
    deck = Deck(title="Safe")
    with pytest.raises(ValueError, match="directories"):
        write_pptx("../escape.pptx", deck)
    with pytest.raises(ValueError, match="Macro-enabled"):
        write_pptx("unsafe.pptm", deck)


def test_pptx_read_refuses_outside_root(_isolate_dirs):
    outside = _isolate_dirs / "outside.pptx"
    Presentation().save(outside)
    with pytest.raises(FileNotFoundError):
        read_pptx(str(outside))
