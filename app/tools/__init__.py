"""Tool registry.

To add a tool: create a module in this package, then add its callable to TOOLS.
That single list is what `build_agent` passes to `create_deep_agent`, so nothing
else needs to change.
"""

from __future__ import annotations

from collections.abc import Callable

from app.tools.search import internet_search
from app.tools.xlsx import Sheet, read_xlsx, write_xlsx

TOOLS: list[Callable] = [
    internet_search,
    write_xlsx,
    read_xlsx,
]

__all__ = ["TOOLS", "Sheet", "internet_search", "read_xlsx", "write_xlsx"]
