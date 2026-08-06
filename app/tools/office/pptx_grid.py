"""Single source of truth for bounded PowerPoint layout geometry."""

from __future__ import annotations

from dataclasses import dataclass

from pptx.util import Inches

WIDE_WIDTH = Inches(13.333333)
WIDE_HEIGHT = Inches(7.5)


@dataclass(frozen=True)
class Grid:
    """Scaled coordinates for the shared 16:9-inspired composition grid."""

    width: int
    height: int

    @property
    def margin(self) -> int:
        return int(self.width * .035)

    @property
    def gap(self) -> int:
        return int(self.width * .025)

    def columns(self, count: int) -> list[tuple[int, int]]:
        column_width = int(
            (self.width - 2 * self.margin - self.gap * (count - 1)) / count
        )
        return [
            (self.margin + index * (column_width + self.gap), column_width)
            for index in range(count)
        ]

    def x(self, fraction: float) -> int:
        return int(self.width * fraction)

    def y(self, fraction: float) -> int:
        return int(self.height * fraction)
