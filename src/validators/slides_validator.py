import re

from google.oauth2.credentials import Credentials

from src.integrations.google.clients import build_slides_client
from src.services.presentation_cache import get_cached_presentation
from src.slides.auth import get_google_credentials
from src.validators.color_utils import (
    extract_rgb_from_slides_color,
    is_allowed_palette_color,
    palette_violation_metadata,
)
from src.validators.location import format_location
from src.validators.models import Severity, ValidationIssue, ValidationResult
from src.validators.section_slides import (
    detect_section_slide,
    validate_section_sequence,
    validate_section_slide,
)
from src.validators.slides_text import (
    collect_slides_text_spans,
    page_size_to_points,
    section_span_keys,
)
from src.validators.text_span_rules import TextSpanContext, validate_text_span


def extract_presentation_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    match = re.search(r"/presentation/d/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]+", url_or_id):
        return url_or_id
    raise ValueError("URL o ID de Google Slides no válido")


class SlidesValidator:
    def __init__(self, credentials: Credentials | None = None) -> None:
        creds = credentials or get_google_credentials()
        self._service = build_slides_client(creds)
        self._credentials = creds

    def validate(self, url_or_id: str) -> ValidationResult:
        presentation_id = extract_presentation_id(url_or_id)
        presentation = get_cached_presentation(self._service, presentation_id)
        slides = presentation.get("slides", [])
        theme_fonts = presentation.get("theme", {}).get("fonts", {})
        page_width, page_height = page_size_to_points(presentation.get("pageSize"))
        issues: list[ValidationIssue] = []
        section_slides = []

        for index, slide in enumerate(slides, start=1):
            slide_number = index
            raw_spans = collect_slides_text_spans(slide, theme_fonts)
            sized_spans = [
                (bbox, text, span)
                for bbox, text, span in raw_spans
                if span.get("size", 0) > 0
            ]
            section_slide = detect_section_slide(
                sized_spans,
                slide_number,
                page_width,
                page_height,
            )
            if section_slide:
                section_slides.append(section_slide)

            issues.extend(
                self._validate_slide(
                    slide,
                    slide_number,
                    page_width,
                    page_height,
                    raw_spans,
                    section_slide,
                )
            )

        issues.extend(validate_section_sequence(section_slides))
        for section_slide in section_slides:
            issues.extend(validate_section_slide(section_slide))

        return ValidationResult(
            source=url_or_id,
            source_type="google_slides",
            total_slides=len(slides),
            issues=issues,
            presentation_id=presentation_id,
        )

    def _validate_slide(
        self,
        slide: dict,
        slide_number: int,
        page_width: float,
        page_height: float,
        raw_spans: list,
        section_slide,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        section_keys = section_span_keys(section_slide)

        page_props = slide.get("slideProperties", {})
        bg_fill = page_props.get("pageBackgroundFill", {})
        bg_color = extract_rgb_from_slides_color(bg_fill.get("solidFill", {}).get("color"))
        if bg_color and not bg_color.startswith("theme:"):
            if not is_allowed_palette_color(bg_color):
                palette = palette_violation_metadata(bg_color)
                issues.append(
                    ValidationIssue(
                        slide_number=slide_number,
                        category="fondo",
                        message="Color de fondo no permitido en la paleta ADG",
                        severity=Severity.POSIBLE,
                        **palette,
                    )
                )

        for element in slide.get("pageElements", []):
            issues.extend(self._validate_element_colors(element, slide_number))

        for bbox, text, span_data in raw_spans:
            ctx = TextSpanContext(
                slide_number=slide_number,
                text=text,
                bbox=bbox,
                page_width=page_width,
                page_height=page_height,
                font=span_data.get("font", ""),
                size=span_data.get("size", 0.0),
                flags=span_data.get("flags", 0),
                color_hex=span_data.get("color_hex"),
                location=format_location(bbox, page_width, page_height),
                is_section_span=(bbox, text) in section_keys,
                object_id=span_data.get("object_id"),
                text_range=span_data.get("text_range"),
            )
            issues.extend(validate_text_span(ctx))

        return issues

    def _validate_element_colors(self, element: dict, slide_number: int) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if "elementGroup" in element:
            for child in element["elementGroup"].get("children", []):
                issues.extend(self._validate_element_colors(child, slide_number))
            return issues

        if "shape" in element:
            fill = element["shape"].get("shapeProperties", {}).get("shapeBackgroundFill", {})
            fill_color = extract_rgb_from_slides_color(fill.get("solidFill", {}).get("color"))
            if fill_color and not fill_color.startswith("theme:"):
                if not is_allowed_palette_color(fill_color):
                    palette = palette_violation_metadata(fill_color)
                    object_id = element.get("objectId")
                    issues.append(
                        ValidationIssue(
                            slide_number=slide_number,
                            category="forma",
                            message="Color de forma no permitido en la paleta ADG",
                            severity=Severity.POSIBLE,
                            object_id=object_id,
                            fix_type="fill_color" if object_id else None,
                            fix_payload={"color": palette["color_suggested"]} if object_id else None,
                            **palette,
                        )
                    )

        return issues
