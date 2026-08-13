from config.brand_guidelines import SUBTITLE_COLOR, SUBTITLE_FONT_SIZE, TITLE_COLOR, TITLE_FONT_SIZE
from src.validators.models import Severity, ValidationIssue
from src.validators.rules import (
    expected_subtitle_description,
    expected_title_description,
    is_bold_font,
    is_header_size_candidate,
    is_light_font,
    size_error_severity,
    sizes_match,
)


def validate_header_subtitle(
    slide_number: int,
    text: str,
    font: str,
    size: float,
    flags: int,
    color_hex: str | None,
    location: str,
    *,
    object_id: str | None = None,
    text_range: dict | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    element = f"Texto «{text[:80]}»"
    fix_base: dict = {}
    if object_id:
        fix_base["object_id"] = object_id
    if text_range:
        fix_base["text_range"] = text_range

    if sizes_match(size, TITLE_FONT_SIZE):
        if not is_bold_font(font, flags):
            issues.append(
                ValidationIssue(
                    slide_number=slide_number,
                    category="peso_fuente",
                    message="Título (superior izquierda): debe ser Bold",
                    expected=expected_title_description(),
                    actual=f"{font}, tamaño {size:.1f}",
                    element=element,
                    location=location,
                    text_preview=text[:80],
                    severity=Severity.GRAVE,
                    fix_type="font_weight" if object_id else None,
                    fix_payload={"bold": True} if object_id else None,
                    **fix_base,
                )
            )
        if color_hex and not color_hex.startswith("theme:"):
            from src.validators.color_utils import colors_match

            if not colors_match(color_hex, TITLE_COLOR):
                issues.append(
                    ValidationIssue(
                        slide_number=slide_number,
                        category="color",
                        message="Título (superior izquierda): color incorrecto",
                        expected=f"Petrol Blue ({TITLE_COLOR})",
                        actual=color_hex,
                        element=element,
                        location=location,
                        text_preview=text[:80],
                        severity=Severity.GRAVE,
                        fix_type="text_color" if object_id else None,
                        fix_payload={"color": TITLE_COLOR} if object_id else None,
                        **fix_base,
                    )
                )
        return issues

    if sizes_match(size, SUBTITLE_FONT_SIZE):
        if not is_light_font(font):
            issues.append(
                ValidationIssue(
                    slide_number=slide_number,
                    category="peso_fuente",
                    message="Subtítulo (superior izquierda): debe ser Light",
                    expected=expected_subtitle_description(),
                    actual=f"{font}, tamaño {size:.1f}",
                    element=element,
                    location=location,
                    text_preview=text[:80],
                    severity=Severity.GRAVE,
                    fix_type="font_weight" if object_id else None,
                    fix_payload={"bold": False, "weight": 300} if object_id else None,
                    **fix_base,
                )
            )
        if color_hex and not color_hex.startswith("theme:"):
            from src.validators.color_utils import colors_match

            if not colors_match(color_hex, SUBTITLE_COLOR):
                issues.append(
                    ValidationIssue(
                        slide_number=slide_number,
                        category="color",
                        message="Subtítulo (superior izquierda): color incorrecto",
                        expected=f"Obsidian Blue ({SUBTITLE_COLOR})",
                        actual=color_hex,
                        element=element,
                        location=location,
                        text_preview=text[:80],
                        severity=Severity.GRAVE,
                        fix_type="text_color" if object_id else None,
                        fix_payload={"color": SUBTITLE_COLOR} if object_id else None,
                        **fix_base,
                    )
                )
        return issues

    if not is_header_size_candidate(size):
        return issues

    closer_to_title = abs(size - TITLE_FONT_SIZE) <= abs(size - SUBTITLE_FONT_SIZE)
    if closer_to_title:
        expected_size = TITLE_FONT_SIZE
        role = "Título"
        expected_desc = expected_title_description()
    else:
        expected_size = SUBTITLE_FONT_SIZE
        role = "Subtítulo"
        expected_desc = expected_subtitle_description()

    severity = size_error_severity(size, expected_size)
    issues.append(
        ValidationIssue(
            slide_number=slide_number,
            category="tamaño",
            message=f"{role} (superior izquierda): tamaño incorrecto",
            expected=expected_desc,
            actual=f"tamaño {size:.1f}, fuente {font}",
            element=element,
            location=location,
            text_preview=text[:80],
            severity=severity,
            fix_type="font_size" if object_id else None,
            fix_payload={"font_size": expected_size} if object_id else None,
            **fix_base,
        )
    )
    return issues
