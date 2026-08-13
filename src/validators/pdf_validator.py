from pathlib import Path

import fitz

from src.validators.color_utils import (
    colors_match,
    int_to_hex,
    is_allowed_palette_color,
    palette_violation_metadata,
)
from src.validators.header_text import validate_header_subtitle
from src.validators.location import (
    describe_graphic_element,
    find_related_text,
    format_location,
)
from src.validators.models import Severity, ValidationIssue, ValidationResult
from src.validators.section_slides import (
    SectionSlideData,
    detect_section_slide,
    validate_section_sequence,
    validate_section_slide,
)
from src.validators.rules import (
    expected_font_description,
    is_approved_font,
    is_index_number,
    is_top_left_aligned,
)


class PDFValidator:
    def validate(self, pdf_path: Path) -> ValidationResult:
        doc = fitz.open(str(pdf_path))
        issues: list[ValidationIssue] = []
        total_slides = len(doc)
        section_slides: list[SectionSlideData] = []

        for page_index in range(total_slides):
            page = doc[page_index]
            slide_number = page_index + 1
            raw_spans = self._collect_text_spans(page)
            section_slide = detect_section_slide(
                raw_spans,
                slide_number,
                page.rect.width,
                page.rect.height,
            )
            if section_slide:
                section_slides.append(section_slide)
            issues.extend(
                self._validate_page(page, slide_number, section_slide=section_slide)
            )

        issues.extend(validate_section_sequence(section_slides))
        for section_slide in section_slides:
            issues.extend(validate_section_slide(section_slide))

        doc.close()
        return ValidationResult(
            source=str(pdf_path),
            source_type="pdf",
            total_slides=total_slides,
            issues=issues,
        )

    def _collect_text_spans(self, page: fitz.Page) -> list[tuple[tuple, str, dict]]:
        spans: list[tuple[tuple, str, dict]] = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    bbox = span.get("bbox", line.get("bbox", block.get("bbox")))
                    if bbox:
                        spans.append((bbox, text, span))
        return spans

    def _validate_page(
        self,
        page: fitz.Page,
        slide_number: int,
        section_slide: SectionSlideData | None = None,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        page_width = page.rect.width
        page_height = page.rect.height
        filled_boxes = self._extract_filled_boxes(page)
        raw_spans = self._collect_text_spans(page)
        text_spans = [(bbox, text) for bbox, text, _ in raw_spans]

        issues.extend(
            self._validate_drawings(page, slide_number, text_spans, page_width, page_height)
        )

        section_span_keys = self._section_span_keys(section_slide)

        for bbox, text, span_data in raw_spans:
            issues.extend(
                self._validate_span(
                    span_data,
                    slide_number,
                    text,
                    bbox,
                    page_width,
                    page_height,
                    filled_boxes,
                    is_section_span=(bbox, text) in section_span_keys,
                )
            )

        return issues

    def _section_span_keys(self, section_slide: SectionSlideData | None) -> set[tuple[tuple, str]]:
        if not section_slide:
            return set()
        keys: set[tuple[tuple, str]] = {(section_slide.number.bbox, section_slide.number.text)}
        for title in section_slide.titles:
            keys.add((title.bbox, title.text))
        for subtitle in section_slide.subtitles:
            keys.add((subtitle.bbox, subtitle.text))
        return keys

    def _extract_filled_boxes(self, page: fitz.Page) -> list[fitz.Rect]:
        boxes: list[fitz.Rect] = []
        page_area = page.rect.width * page.rect.height
        for draw in page.get_drawings():
            if not draw.get("fill"):
                continue
            rect = draw.get("rect")
            if not rect:
                continue
            r = fitz.Rect(rect)
            area = r.width * r.height
            if area < page_area * 0.004 or area > page_area * 0.85:
                continue
            boxes.append(r)
        return boxes

    def _is_decorative_stroke(self, draw: dict, draw_rect: fitz.Rect) -> bool:
        if draw.get("fill"):
            return False
        if not draw.get("color"):
            return True
        if draw_rect.height < 1 or draw_rect.width < 1:
            return True
        if draw_rect.width * draw_rect.height < 50:
            items = draw.get("items") or []
            if items and all(item[0] in ("l", "c") for item in items):
                return True
        return False

    def _is_inside_box(self, bbox: tuple, boxes: list[fitz.Rect]) -> bool:
        text_rect = fitz.Rect(bbox)
        cx = (text_rect.x0 + text_rect.x1) / 2
        cy = (text_rect.y0 + text_rect.y1) / 2
        for box in boxes:
            if box.contains((cx, cy)) or box.contains(text_rect):
                return True
        return False

    def _validate_drawings(
        self,
        page: fitz.Page,
        slide_number: int,
        text_spans: list[tuple[tuple, str]],
        page_width: float,
        page_height: float,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for draw in page.get_drawings():
            rect = draw.get("rect")
            if not rect:
                continue
            draw_rect = fitz.Rect(rect)
            bbox = tuple(draw_rect)
            location = format_location(bbox, page_width, page_height)
            related = find_related_text(draw_rect, text_spans, page_height)

            for key, label in (("fill", "relleno"), ("color", "trazo")):
                color = draw.get(key)
                if not color:
                    continue
                if key == "color" and self._is_decorative_stroke(draw, draw_rect):
                    continue
                hex_color = rgb_to_hex_tuple(color)
                if hex_color and not is_allowed_palette_color(hex_color):
                    palette = palette_violation_metadata(hex_color)
                    element = describe_graphic_element(draw, related, label)
                    issues.append(
                        ValidationIssue(
                            slide_number=slide_number,
                            category="color",
                            message=f"Color de {label} no permitido en la paleta ADG",
                            element=element,
                            location=location,
                            text_preview=related,
                            severity=Severity.POSIBLE,
                            **palette,
                        )
                    )
        return issues

    def _validate_span(
        self,
        span: dict,
        slide_number: int,
        text: str,
        bbox: tuple,
        page_width: float,
        page_height: float,
        filled_boxes: list[fitz.Rect],
        is_section_span: bool = False,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        font = span["font"]
        size = span["size"]
        flags = span.get("flags", 0)
        color_hex = int_to_hex(span["color"])
        location = format_location(bbox, page_width, page_height)
        element = f"Texto «{text[:80]}»"

        if not is_allowed_palette_color(color_hex):
            palette = palette_violation_metadata(color_hex)
            issues.append(
                ValidationIssue(
                    slide_number=slide_number,
                    category="color",
                    message="Color de texto no permitido en la paleta ADG",
                    element=element,
                    location=location,
                    text_preview=text[:80],
                    severity=Severity.POSIBLE,
                    **palette,
                )
            )

        if not is_approved_font(font):
            issues.append(
                ValidationIssue(
                    slide_number=slide_number,
                    category="tipografía",
                    message="Fuente no permitida",
                    expected=expected_font_description(),
                    actual=font,
                    element=element,
                    location=location,
                    text_preview=text[:80],
                    severity=Severity.GRAVE,
                )
            )

        if is_section_span:
            return issues

        if not is_top_left_aligned(bbox, page_width, page_height):
            return issues

        if self._is_inside_box(bbox, filled_boxes):
            return issues

        if is_index_number(text):
            return issues

        issues.extend(
            validate_header_subtitle(
                slide_number, text, font, size, flags, color_hex, location
            )
        )
        return issues


def rgb_to_hex_tuple(rgb: tuple) -> str | None:
    if not rgb or len(rgb) < 3:
        return None
    r, g, b = rgb[0], rgb[1], rgb[2]
    return f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
