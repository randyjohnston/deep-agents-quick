"""Typed PPTX generation and bounded text extraction."""

from __future__ import annotations

from pptx import Presentation
from pydantic import BaseModel, Field

from app.tools.office.paths import resolve_read_path, resolve_write_path

# python-pptx pulls in XlsxWriter for chart workbooks. Spreadsheet generation
# intentionally remains in xlsx.py with openpyxl so there is one XLSX code path.


class Slide(BaseModel):
    """One presentation slide with a title and concise bullet points."""

    title: str = Field(description="Slide title")
    bullets: list[str] = Field(default_factory=list, description="Slide bullet points")


class Deck(BaseModel):
    """The structured content of one PowerPoint deck."""

    title: str | None = Field(default=None, description="Optional title-slide heading")
    subtitle: str | None = Field(default=None, description="Optional title-slide subtitle")
    slides: list[Slide] = Field(default_factory=list)


def write_pptx(filename: str, deck: Deck) -> str:
    """Create a PowerPoint .pptx file from typed content and return its path.

    Args:
        filename: Output basename. The .pptx extension is added when absent.
        deck: Optional title slide followed by titled bullet slides.
    """
    if not deck.title and not deck.subtitle and not deck.slides:
        raise ValueError("Provide a title, subtitle, or at least one slide.")
    path = resolve_write_path(filename, ".pptx")
    path.parent.mkdir(parents=True, exist_ok=True)
    presentation = Presentation()
    if deck.title or deck.subtitle:
        slide = presentation.slides.add_slide(presentation.slide_layouts[0])
        slide.shapes.title.text = deck.title or ""
        slide.placeholders[1].text = deck.subtitle or ""
    for item in deck.slides:
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = item.title
        frame = slide.placeholders[1].text_frame
        frame.clear()
        for index, bullet in enumerate(item.bullets):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0
    presentation.save(path)
    return f"Wrote {path} — {len(presentation.slides)} slides"


def read_pptx(path: str, max_slides: int = 100) -> str:
    """Extract visible text from a permitted .pptx file."""
    if max_slides < 1:
        raise ValueError("max_slides must be at least 1.")
    resolved = resolve_read_path(path, (".pptx",))
    presentation = Presentation(resolved)
    blocks = [f"# {resolved}", ""]
    for index, slide in enumerate(presentation.slides, start=1):
        if index > max_slides:
            break
        blocks.append(f"## Slide {index}")
        text = [shape.text for shape in slide.shapes if hasattr(shape, "text") and shape.text.strip()]
        blocks.extend(text or ["(empty)"])
        blocks.append("")
    if len(presentation.slides) > max_slides:
        blocks.append(f"... truncated at {max_slides} slides; raise max_slides for more")
    return "\n".join(blocks).rstrip()
