from dataclasses import dataclass
from typing import Any

from src.validators.color_utils import is_allowed_palette_color, palette_violation_metadata
from src.validators.header_text import validate_header_subtitle
from src.validators.models import Severity, ValidationIssue
from src.validators.rules import expected_font_description, is_approved_font, is_index_number, is_top_left_aligned


@dataclass
class TextSpanContext:
    slide_number: int
    text: str
    bbox: tuple
    page_width: float
    page_height: float
    font: str
    size: float
    flags: int
    color_hex: str | None
    location: str
    is_section_span: bool = False
    object_id: str | None = None
    text_range: dict[str, int] | None = None
    extra_skip: bool = False


def validate_text_span(ctx: TextSpanContext) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    element = f"Texto «{ctx.text[:80]}»"

    if ctx.color_hex and not ctx.color_hex.startswith("theme:"):
        if not is_allowed_palette_color(ctx.color_hex):
            palette = palette_violation_metadata(ctx.color_hex)
            fix_fields: dict[str, Any] = {}
            if ctx.object_id:
                fix_fields["object_id"] = ctx.object_id
                fix_fields["fix_type"] = "text_color"
                fix_fields["fix_payload"] = {"color": palette["color_suggested"]}
            if ctx.text_range:
                fix_fields["text_range"] = ctx.text_range
            issues.append(
                ValidationIssue(
                    slide_number=ctx.slide_number,
                    category="color",
                    message="Color de texto no permitido en la paleta ADG",
                    element=element,
                    location=ctx.location,
                    text_preview=ctx.text[:80],
                    severity=Severity.POSIBLE,
                    **fix_fields,
                    **palette,
                )
            )

    if ctx.font and not is_approved_font(ctx.font):
        from config.brand_guidelines import BRAND_FONT
        fix_fields = {}
        if ctx.object_id:
            fix_fields["object_id"] = ctx.object_id
            fix_fields["fix_type"] = "font_family"
            fix_fields["fix_payload"] = {"font_family": BRAND_FONT}
        if ctx.text_range:
            fix_fields["text_range"] = ctx.text_range
        issues.append(
            ValidationIssue(
                slide_number=ctx.slide_number,
                category="tipografía",
                message="Fuente no permitida",
                expected=expected_font_description(),
                actual=ctx.font,
                element=element,
                location=ctx.location,
                text_preview=ctx.text[:80],
                severity=Severity.GRAVE,
                **fix_fields,
            )
        )

    if ctx.is_section_span or ctx.extra_skip:
        return issues

    if ctx.size <= 0:
        return issues

    if not is_top_left_aligned(ctx.bbox, ctx.page_width, ctx.page_height):
        return issues

    if is_index_number(ctx.text):
        return issues

    issues.extend(
        validate_header_subtitle(
            ctx.slide_number,
            ctx.text,
            ctx.font,
            ctx.size,
            ctx.flags,
            ctx.color_hex,
            ctx.location,
            object_id=ctx.object_id,
            text_range=ctx.text_range,
        )
    )
    return issues
