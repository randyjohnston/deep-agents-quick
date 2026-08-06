"""Typed PPTX generation and bounded text extraction."""

from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Inches
from pydantic import BaseModel, Field

from app.tools.office.paths import (
    load_office_file,
    load_office_template,
    resolve_read_path,
    resolve_template_path,
    resolve_write_path,
)
from app.tools.office.theme import ResolvedTheme, Theme, resolve_theme

_POTX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
)
_PPTX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)

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


def write_pptx(
    filename: str,
    deck: Deck,
    theme: Theme | None = None,
    template: str | None = None,
) -> str:
    """Create a PowerPoint .pptx file from typed content and return its path.

    Args:
        filename: Output basename. The .pptx extension is added when absent.
        deck: Optional title slide followed by titled bullet slides.
        theme: Bounded inline branding or a named theme reference.
        template: Optional .potx/.pptx template under OFFICE_INPUT_DIR.
    """
    if not deck.title and not deck.subtitle and not deck.slides:
        raise ValueError("Provide a title, subtitle, or at least one slide.")
    path = resolve_write_path(filename, ".pptx")
    path.parent.mkdir(parents=True, exist_ok=True)
    template_path = resolve_template_path(template, (".potx", ".pptx")) if template else None
    presentation = (
        load_office_template(template_path, Presentation, _POTX_CONTENT_TYPE, _PPTX_CONTENT_TYPE)
        if template_path
        else Presentation()
    )
    branding = resolve_theme(theme)
    if deck.title or deck.subtitle:
        layout, body_idx = _content_layout(presentation, "Title Slide", 0)
        slide = presentation.slides.add_slide(layout)
        slide.shapes.title.text = deck.title or ""
        _placeholder(slide, body_idx).text = deck.subtitle or ""
        _style_slide(slide, branding)
        _add_logo(slide, presentation, branding)
    for item in deck.slides:
        layout, body_idx = _content_layout(presentation, "Title and Content", 1)
        slide = presentation.slides.add_slide(layout)
        slide.shapes.title.text = item.title
        frame = _placeholder(slide, body_idx).text_frame
        frame.clear()
        for index, bullet in enumerate(item.bullets):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0
        _style_slide(slide, branding)
        _add_logo(slide, presentation, branding)
    presentation.save(path)
    return f"Wrote {path} — {len(presentation.slides)} slides"


def _content_layout(presentation, preferred_name: str, fallback_index: int):
    """Select a layout and ensure it has title and body text placeholders."""
    layout = None
    for layout in presentation.slide_layouts:
        if layout.name.casefold() == preferred_name.casefold():
            break
    else:
        layout = None
    if layout is None and len(presentation.slide_layouts) <= fallback_index:
        raise ValueError(f"Presentation template has no usable {preferred_name!r} layout")
    layout = layout or presentation.slide_layouts[fallback_index]
    title = next(
        (
            placeholder
            for placeholder in layout.placeholders
            if placeholder.placeholder_format.type
            in {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE}
        ),
        None,
    )
    if title is None:
        raise ValueError(
            f"Presentation template layout {layout.name!r} must contain title and body placeholders"
        )
    body = next(
        (
            placeholder
            for placeholder in layout.placeholders
            if placeholder.shape_id != title.shape_id
            and getattr(placeholder, "has_text_frame", False)
        ),
        None,
    )
    if body is None:
        raise ValueError(
            f"Presentation template layout {layout.name!r} must contain title and body placeholders"
        )
    return layout, body.placeholder_format.idx


def _placeholder(slide, idx: int):
    """Return the slide placeholder matching a validated layout placeholder."""
    return next(
        placeholder
        for placeholder in slide.placeholders
        if placeholder.placeholder_format.idx == idx
    )


def _style_slide(slide, theme: ResolvedTheme | None) -> None:
    if not theme:
        return
    title = slide.shapes.title
    if title:
        if theme.header_background:
            title.fill.solid()
            title.fill.fore_color.rgb = RGBColor.from_string(theme.header_background)
        _style_text(title.text_frame, theme.heading_font, theme.header_foreground, bold=True)
    for shape in slide.placeholders:
        if (title and shape.shape_id == title.shape_id) or not getattr(
            shape, "has_text_frame", False
        ):
            continue
        _style_text(shape.text_frame, theme.body_font, theme.accent_color)


def _style_text(frame, font_name: str | None, color: str | None, bold: bool = False) -> None:
    for paragraph in frame.paragraphs:
        for run in paragraph.runs:
            if font_name:
                run.font.name = font_name
            if color:
                run.font.color.rgb = RGBColor.from_string(color)
            if bold:
                run.font.bold = True


def _add_logo(slide, presentation, theme: ResolvedTheme | None) -> None:
    if not theme or not theme.logo:
        return
    width = Inches(1)
    slide.shapes.add_picture(
        str(theme.logo), presentation.slide_width - width - Inches(0.25), Inches(0.1), width=width
    )


def read_pptx(path: str, max_slides: int = 100) -> str:
    """Extract visible text from a permitted .pptx file."""
    if max_slides < 1:
        raise ValueError("max_slides must be at least 1.")
    resolved = resolve_read_path(path, (".pptx",))
    presentation = load_office_file(resolved, Presentation)
    blocks = [f"# {resolved}", ""]
    for index, slide in enumerate(presentation.slides, start=1):
        if index > max_slides:
            break
        blocks.append(f"## Slide {index}")
        text = [value for shape in slide.shapes for value in _shape_text(shape)]
        blocks.extend(text or ["(empty)"])
        blocks.append("")
    if len(presentation.slides) > max_slides:
        blocks.append(f"... truncated at {max_slides} slides; raise max_slides for more")
    return "\n".join(blocks).rstrip()


def _shape_text(shape) -> list[str]:
    """Return visible text from text frames, tables, and nested shape groups."""
    if getattr(shape, "has_table", False):
        return [
            " | ".join(cell.text for cell in row.cells)
            for row in shape.table.rows
            if any(cell.text.strip() for cell in row.cells)
        ]
    if hasattr(shape, "shapes"):
        return [value for child in shape.shapes for value in _shape_text(child)]
    text = getattr(shape, "text", "")
    return [text] if text.strip() else []
