import re
from dataclasses import dataclass, field

from config.brand_guidelines import (
    BRAND_FONT,
    SECTION_NUMBER_FONT_SIZE,
    SECTION_NUMBER_MIN_DETECT_SIZE,
    SECTION_SUBTITLE_FONT_SIZE,
    SECTION_TITLE_FONT_SIZE,
)
from src.validators.location import format_location
from src.validators.models import Severity, ValidationIssue
from src.validators.rules import (
    is_bold_font,
    size_error_severity,
    sizes_match,
)

SECTION_NUMBER_PATTERN = re.compile(r"^(\d{1,2})\.$")


@dataclass
class SectionTextSpan:
    text: str
    size: float
    font: str
    flags: int
    bbox: tuple
    location: str = ""
    object_id: str | None = None
    text_range: dict | None = None


@dataclass
class SectionSlideData:
    slide_number: int
    section_num: int
    section_label: str
    number: SectionTextSpan
    titles: list[SectionTextSpan] = field(default_factory=list)
    subtitles: list[SectionTextSpan] = field(default_factory=list)


def is_section_number_text(text: str) -> bool:
    return bool(SECTION_NUMBER_PATTERN.match(text.strip()))


def parse_section_number(text: str) -> int | None:
    match = SECTION_NUMBER_PATTERN.match(text.strip())
    if not match:
        return None
    return int(match.group(1))


def is_uppercase_text(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return True
    return all(char.isupper() for char in letters)


def _span_role(size: float) -> str:
    title_distance = abs(size - SECTION_TITLE_FONT_SIZE)
    subtitle_distance = abs(size - SECTION_SUBTITLE_FONT_SIZE)
    if subtitle_distance < title_distance and size <= SECTION_TITLE_FONT_SIZE:
        return "subtitle"
    return "title"


def detect_section_slide(
    raw_spans: list[tuple[tuple, str, dict]],
    slide_number: int,
    page_width: float,
    page_height: float,
) -> SectionSlideData | None:
    if not raw_spans:
        return None

    max_size = max(span["size"] for _, _, span in raw_spans)
    number_spans: list[tuple[tuple, str, dict]] = []
    for bbox, text, span in raw_spans:
        if not is_section_number_text(text):
            continue
        if span["size"] < SECTION_NUMBER_MIN_DETECT_SIZE:
            continue
        if span["size"] < max_size * 0.9:
            continue
        number_spans.append((bbox, text, span))

    if len(number_spans) != 1:
        return None

    number_bbox, number_text, number_span = number_spans[0]
    section_num = parse_section_number(number_text)
    if section_num is None:
        return None

    other_spans = [
        (bbox, text, span)
        for bbox, text, span in raw_spans
        if (bbox, text, span) != (number_bbox, number_text, number_span)
    ]
    if not other_spans or len(other_spans) > 4:
        return None

    number = SectionTextSpan(
        text=number_text,
        size=number_span["size"],
        font=number_span["font"],
        flags=number_span.get("flags", 0),
        bbox=number_bbox,
        location=format_location(number_bbox, page_width, page_height),
        object_id=number_span.get("object_id"),
        text_range=number_span.get("text_range"),
    )

    titles: list[SectionTextSpan] = []
    subtitles: list[SectionTextSpan] = []
    for bbox, text, span in other_spans:
        item = SectionTextSpan(
            text=text,
            size=span["size"],
            font=span["font"],
            flags=span.get("flags", 0),
            bbox=bbox,
            location=format_location(bbox, page_width, page_height),
            object_id=span.get("object_id"),
            text_range=span.get("text_range"),
        )
        if _span_role(span["size"]) == "subtitle":
            subtitles.append(item)
        else:
            titles.append(item)

    if not titles:
        return None

    return SectionSlideData(
        slide_number=slide_number,
        section_num=section_num,
        section_label=number_text,
        number=number,
        titles=titles,
        subtitles=subtitles,
    )


def validate_section_slide(data: SectionSlideData) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_validate_section_number(data))
    for title in data.titles:
        issues.extend(_validate_section_title(data.slide_number, title))
    for subtitle in data.subtitles:
        issues.extend(_validate_section_subtitle(data.slide_number, subtitle))
    return issues


def validate_section_sequence(section_slides: list[SectionSlideData]) -> list[ValidationIssue]:
    if len(section_slides) < 2:
        return []

    ordered = sorted(section_slides, key=lambda item: item.slide_number)
    issues: list[ValidationIssue] = []
    seen: dict[int, int] = {}
    expected = 1

    for item in ordered:
        if item.section_num in seen:
            first_slide = seen[item.section_num]
            issues.append(
                ValidationIssue(
                    slide_number=item.slide_number,
                    category="numeración",
                    message=f"Número de sección duplicado «{item.section_label}»",
                    expected="Cada sección con un número único",
                    actual=f"Ya usado en diapositiva {first_slide}",
                    element=f"Número de sección «{item.section_label}»",
                    severity=Severity.GRAVE,
                )
            )
            continue

        seen[item.section_num] = item.slide_number

        if item.section_num != expected:
            if item.section_num > expected:
                missing = list(range(expected, item.section_num))
                missing_label = ", ".join(f"{num:02d}." for num in missing)
                issues.append(
                    ValidationIssue(
                        slide_number=item.slide_number,
                        category="numeración",
                        message="Secuencia de secciones con salto",
                        expected=f"Continuar con «{expected:02d}.»",
                        actual=f"Aparece «{item.section_label}» (falta {missing_label})",
                        element=f"Número de sección «{item.section_label}»",
                        severity=Severity.GRAVE,
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        slide_number=item.slide_number,
                        category="numeración",
                        message="Secuencia de secciones fuera de orden",
                        expected=f"Continuar con «{expected:02d}.»",
                        actual=f"Aparece «{item.section_label}»",
                        element=f"Número de sección «{item.section_label}»",
                        severity=Severity.GRAVE,
                    )
                )
            expected = item.section_num + 1
            continue

        expected = item.section_num + 1

    return issues


def _section_fix_fields(span: SectionTextSpan) -> dict:
    if not span.object_id:
        return {}
    return {
        "object_id": span.object_id,
        "text_range": span.text_range,
    }


def _validate_section_number(data: SectionSlideData) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    number = data.number
    element = f"Número de sección «{number.text}»"
    fix_fields = _section_fix_fields(number)

    if not is_bold_font(number.font, number.flags):
        issues.append(
            ValidationIssue(
                slide_number=data.slide_number,
                category="peso_fuente",
                message="Número de sección: debe ser Bold",
                expected=f"{BRAND_FONT} Bold, tamaño {SECTION_NUMBER_FONT_SIZE}",
                actual=f"{number.font}, tamaño {number.size:.1f}",
                element=element,
                location=number.location,
                text_preview=number.text,
                severity=Severity.GRAVE,
                fix_type="font_weight" if number.object_id else None,
                fix_payload={"bold": True} if number.object_id else None,
                **fix_fields,
            )
        )

    if sizes_match(number.size, SECTION_NUMBER_FONT_SIZE):
        return issues

    severity = size_error_severity(number.size, SECTION_NUMBER_FONT_SIZE)
    issues.append(
        ValidationIssue(
            slide_number=data.slide_number,
            category="tamaño",
            message="Número de sección: tamaño incorrecto",
            expected=f"{BRAND_FONT} Bold, tamaño {SECTION_NUMBER_FONT_SIZE}",
            actual=f"tamaño {number.size:.1f}, fuente {number.font}",
            element=element,
            location=number.location,
            text_preview=number.text,
            severity=severity,
            fix_type="font_size" if number.object_id else None,
            fix_payload={"font_size": SECTION_NUMBER_FONT_SIZE} if number.object_id else None,
            **fix_fields,
        )
    )
    return issues


def _validate_section_title(slide_number: int, title: SectionTextSpan) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    element = f"Título de sección «{title.text[:80]}»"
    fix_fields = _section_fix_fields(title)

    if not is_bold_font(title.font, title.flags):
        issues.append(
            ValidationIssue(
                slide_number=slide_number,
                category="peso_fuente",
                message="Título de sección: debe ser Bold",
                expected=f"{BRAND_FONT} Bold, tamaño {SECTION_TITLE_FONT_SIZE}",
                actual=f"{title.font}, tamaño {title.size:.1f}",
                element=element,
                location=title.location,
                text_preview=title.text[:80],
                severity=Severity.GRAVE,
                fix_type="font_weight" if title.object_id else None,
                fix_payload={"bold": True} if title.object_id else None,
                **fix_fields,
            )
        )

    if sizes_match(title.size, SECTION_TITLE_FONT_SIZE):
        return issues

    severity = size_error_severity(title.size, SECTION_TITLE_FONT_SIZE)
    issues.append(
        ValidationIssue(
            slide_number=slide_number,
            category="tamaño",
            message="Título de sección: tamaño incorrecto",
            expected=f"{BRAND_FONT} Bold, tamaño {SECTION_TITLE_FONT_SIZE}",
            actual=f"tamaño {title.size:.1f}, fuente {title.font}",
            element=element,
            location=title.location,
            text_preview=title.text[:80],
            severity=severity,
            fix_type="font_size" if title.object_id else None,
            fix_payload={"font_size": SECTION_TITLE_FONT_SIZE} if title.object_id else None,
            **fix_fields,
        )
    )
    return issues


def _validate_section_subtitle(slide_number: int, subtitle: SectionTextSpan) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    element = f"Subtítulo de sección «{subtitle.text[:80]}»"
    fix_fields = _section_fix_fields(subtitle)

    if not is_uppercase_text(subtitle.text):
        issues.append(
            ValidationIssue(
                slide_number=slide_number,
                category="formato",
                message="Subtítulo de sección: debe estar en mayúsculas",
                expected="Texto en MAYÚSCULAS",
                actual=subtitle.text[:80],
                element=element,
                location=subtitle.location,
                text_preview=subtitle.text[:80],
                severity=Severity.GRAVE,
            )
        )

    if sizes_match(subtitle.size, SECTION_SUBTITLE_FONT_SIZE):
        return issues

    severity = size_error_severity(subtitle.size, SECTION_SUBTITLE_FONT_SIZE)
    issues.append(
        ValidationIssue(
            slide_number=slide_number,
            category="tamaño",
            message="Subtítulo de sección: tamaño incorrecto",
            expected=f"{BRAND_FONT}, tamaño {SECTION_SUBTITLE_FONT_SIZE}",
            actual=f"tamaño {subtitle.size:.1f}, fuente {subtitle.font}",
            element=element,
            location=subtitle.location,
            text_preview=subtitle.text[:80],
            severity=severity,
            fix_type="font_size" if subtitle.object_id else None,
            fix_payload={"font_size": SECTION_SUBTITLE_FONT_SIZE} if subtitle.object_id else None,
            **fix_fields,
        )
    )
    return issues
