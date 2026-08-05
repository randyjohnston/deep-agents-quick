"""Compatibility imports for the original XLSX module path."""

from app.tools.office.xlsx import Sheet, read_xlsx, write_xlsx

__all__ = ["Sheet", "read_xlsx", "write_xlsx"]
