"""Office file tool registry and typed content models."""

from app.tools.office.docx import Document, Section, read_docx, write_docx
from app.tools.office.images import fetch_images
from app.tools.office.pptx import (
    Card, CardsSlide, CoverSlide, Deck, Slide, Stat, StatementSlide, StatsSlide,
    read_pptx, write_pptx,
)
from app.tools.office.theme import Theme
from app.tools.office.xlsx import Sheet, read_xlsx, write_xlsx

OFFICE_TOOLS = [
    write_xlsx, read_xlsx, write_docx, read_docx, write_pptx, read_pptx, fetch_images,
]

__all__ = [
    "OFFICE_TOOLS", "Card", "CardsSlide", "CoverSlide", "Deck", "Document", "Section",
    "Sheet", "Slide", "Stat", "StatementSlide", "StatsSlide", "Theme",
    "fetch_images", "read_docx", "read_pptx", "read_xlsx", "write_docx", "write_pptx",
    "write_xlsx",
]
