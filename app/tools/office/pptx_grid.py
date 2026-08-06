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

    @property
    def content_top(self) -> int:
        return self.y(.27)

    @property
    def content_height(self) -> int:
        return self.y(.50)

    @property
    def image_height(self) -> int:
        return self.y(.29)

    @property
    def footer_rule_y(self) -> int:
        return self.y(.908)

    @property
    def footer_text_y(self) -> int:
        return self.y(.92)

    @property
    def cover_panel_width(self) -> int:
        return self.x(.58)

    @property
    def cover_left(self) -> int:
        return self.x(.055)

    @property
    def statement_left(self) -> int:
        return self.x(.085)

    @property
    def cover_kicker_y(self) -> int:
        return self.y(.10)

    @property
    def cover_title_y(self) -> int:
        return self.y(.23)

    @property
    def cover_subtitle_y(self) -> int:
        return self.y(.61)

    @property
    def cover_meta_y(self) -> int:
        return self.y(.84)

    @property
    def chrome_kicker_y(self) -> int:
        return self.y(.035)

    @property
    def chrome_headline_y(self) -> int:
        return self.y(.075)

    @property
    def chrome_deck_y(self) -> int:
        return self.y(.15)

    @property
    def chrome_rule_y(self) -> int:
        return self.y(.205)

    @property
    def statement_rule_y(self) -> int:
        return self.y(.18)

    @property
    def statement_kicker_y(self) -> int:
        return self.y(.17)

    @property
    def statement_text_y(self) -> int:
        return self.y(.29)

    @property
    def statement_attribution_y(self) -> int:
        return self.y(.76)

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
