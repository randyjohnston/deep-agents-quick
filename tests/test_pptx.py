from __future__ import annotations

import pytest
from pptx import Presentation
from pptx.util import Inches

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


def test_pptx_rejects_macro_extension(_isolate_dirs):
    deck = Deck(title="Safe")
    with pytest.raises(ValueError, match="Macro-enabled"):
        write_pptx("unsafe.pptm", deck)


def test_pptx_read_includes_table_text(_isolate_dirs):
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    slide.shapes.title.text = "Q3 Numbers"
    table = slide.shapes.add_table(1, 2, 0, 0, Inches(4), Inches(1)).table
    table.cell(0, 0).text = "EMEA"
    table.cell(0, 1).text = "4200000"
    path = _isolate_dirs / "in" / "table.pptx"
    presentation.save(path)

    output = read_pptx("table.pptx")
    assert "Q3 Numbers" in output
    assert "EMEA | 4200000" in output


def test_pptx_read_recurses_into_grouped_shapes(_isolate_dirs):
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    group = slide.shapes.add_group_shape()
    textbox = group.shapes.add_textbox(0, 0, Inches(4), Inches(1))
    textbox.text = "Nested takeaway"
    path = _isolate_dirs / "in" / "group.pptx"
    presentation.save(path)

    assert "Nested takeaway" in read_pptx("group.pptx")
