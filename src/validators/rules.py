import re

from config.brand_guidelines import (
    APPROVED_FONTS,
    BRAND_FONT,
    FONT_SIZE_TOLERANCE,
    LEFT_REGION_RATIO,
    SIZE_MAJOR_TOLERANCE,
    SUBTITLE_COLOR,
    SUBTITLE_FONT_SIZE,
    TEXT_RULES,
    TITLE_COLOR,
    TITLE_FONT_SIZE,
    TOP_REGION_RATIO,
)
from src.validators.models import Severity


def is_approved_font(font_family: str | None) -> bool:
    if not font_family:
        return False
    normalized = font_family.lower().replace(" ", "").replace("-", "")
    if normalized.startswith("theme:"):
        return False
    return any(approved.replace(" ", "").replace("-", "") in normalized for approved in APPROVED_FONTS)


def extract_style_font_family(style: dict | None) -> str | None:
    if not style:
        return None
    font = style.get("fontFamily")
    if font:
        return str(font)
    weighted = style.get("weightedFontFamily") or {}
    font = weighted.get("fontFamily")
    return str(font) if font else None


def extract_style_font_size(style: dict | None) -> float | None:
    if not style:
        return None
    font_size = style.get("fontSize")
    if not font_size:
        return None
    magnitude = font_size.get("magnitude")
    if magnitude is None:
        return None
    return float(magnitude)


def resolve_slides_font_size(
    run_style: dict,
    paragraph_style: dict | None,
) -> float | None:
    for style in (run_style, paragraph_style or {}):
        size = extract_style_font_size(style)
        if size is not None:
            return size
    return None


def resolve_slides_font_family(
    run_style: dict,
    paragraph_style: dict | None,
    placeholder_type: str | None,
    theme_fonts: dict | None,
) -> str | None:
    for style in (run_style, paragraph_style or {}):
        font = extract_style_font_family(style)
        if font and not font.startswith("theme:"):
            return font

    if not theme_fonts:
        return None

    normalized_ph = (placeholder_type or "").upper()
    if normalized_ph in ("TITLE", "CENTERED_TITLE", "SUBTITLE"):
        title_font = theme_fonts.get("titleFontFamily")
        if title_font and not str(title_font).startswith("theme:"):
            return str(title_font)

    body_font = theme_fonts.get("bodyFontFamily")
    if body_font and not str(body_font).startswith("theme:"):
        return str(body_font)

    return None


def is_bold_font(font_name: str, flags: int = 0) -> bool:
    name = font_name.lower()
    if "bold" in name:
        return True
    if "light" in name or "italic" in name:
        return False
    return bool(flags & 2**4)


def is_light_font(font_name: str) -> bool:
    return "light" in font_name.lower()


def is_index_number(text: str) -> bool:
    return bool(re.match(r"^\d{1,2}\.?$", text.strip()))


def is_header_size_candidate(size: float) -> bool:
    return (
        abs(size - TITLE_FONT_SIZE) <= SIZE_MAJOR_TOLERANCE
        or abs(size - SUBTITLE_FONT_SIZE) <= SIZE_MAJOR_TOLERANCE
    )


def is_top_left_aligned(bbox: tuple, page_width: float, page_height: float) -> bool:
    x0, y0, _, _ = bbox
    in_top = y0 <= page_height * TOP_REGION_RATIO
    in_left = x0 <= page_width * LEFT_REGION_RATIO
    return in_top and in_left


def sizes_match(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= FONT_SIZE_TOLERANCE


def size_error_severity(actual: float, expected: float) -> Severity:
    if abs(actual - expected) > SIZE_MAJOR_TOLERANCE:
        return Severity.POSIBLE
    return Severity.GRAVE


def expected_font_description() -> str:
    return BRAND_FONT


def expected_title_description() -> str:
    return f"{BRAND_FONT} Bold, {TITLE_COLOR}, tamaño {TITLE_FONT_SIZE}"


def expected_subtitle_description() -> str:
    return f"{BRAND_FONT} Light, {SUBTITLE_COLOR}, tamaño {SUBTITLE_FONT_SIZE}"


def get_text_role(
    placeholder_type: str | None,
    bold: bool,
    font_size: float | None,
) -> str:
    if placeholder_type:
        normalized = placeholder_type.upper()
        if normalized in ("TITLE", "CENTERED_TITLE"):
            return "header"
        if normalized == "SUBTITLE":
            return "subtitle"
        if normalized in ("BODY", "BODY_WITH_OVERLAY"):
            return "body"

    if font_size is not None:
        if abs(font_size - TITLE_FONT_SIZE) <= SIZE_MAJOR_TOLERANCE:
            return "header"
        if abs(font_size - SUBTITLE_FONT_SIZE) <= SIZE_MAJOR_TOLERANCE:
            return "subtitle"

    if bold:
        return "header"

    return "body"


def expected_text_description(role: str) -> str:
    rule = TEXT_RULES[role]
    parts = [BRAND_FONT]
    if rule["bold"]:
        parts.append("Bold")
    elif rule["light"]:
        parts.append("Light")
    else:
        parts.append("Regular")
    parts.append(f"color {rule['color']}")
    if rule["font_size"] is not None:
        parts.append(f"tamaño {rule['font_size']}")
    return ", ".join(parts)
