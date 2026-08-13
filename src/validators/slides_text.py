from __future__ import annotations

from typing import Any

from src.validators.rules import (
    is_bold_font,
    is_light_font,
    resolve_slides_font_family,
    resolve_slides_font_size,
)

EMU_PER_POINT = 914400 / 72


def emu_to_points(value: float) -> float:
    return value / EMU_PER_POINT


def dimension_to_points(dimension: dict | None) -> float:
    if not dimension:
        return 0.0
    magnitude = dimension.get("magnitude")
    if magnitude is None:
        return 0.0
    unit = dimension.get("unit", "EMU")
    if unit == "PT":
        return float(magnitude)
    return emu_to_points(float(magnitude))


def page_size_to_points(page_size: dict | None) -> tuple[float, float]:
    if not page_size:
        return 720.0, 405.0
    return (
        dimension_to_points(page_size.get("width")),
        dimension_to_points(page_size.get("height")),
    )


def _weighted_font(style: dict) -> tuple[str | None, int | None]:
    weighted = style.get("weightedFontFamily") or {}
    family = weighted.get("fontFamily")
    weight = weighted.get("weight")
    return (str(family) if family else None, int(weight) if weight is not None else None)


def resolve_slides_bold(
    run_style: dict,
    paragraph_style: dict | None,
    font_family: str | None,
) -> bool:
    paragraph_style = paragraph_style or {}
    if "bold" in run_style:
        return bool(run_style["bold"])
    if "bold" in paragraph_style:
        return bool(paragraph_style["bold"])

    for style in (run_style, paragraph_style):
        _, weight = _weighted_font(style)
        if weight is not None:
            if weight >= 600:
                return True
            if weight <= 450:
                return False

    if font_family:
        return is_bold_font(font_family, 0)
    return False


def resolve_slides_light(
    run_style: dict,
    paragraph_style: dict | None,
    font_family: str | None,
) -> bool:
    paragraph_style = paragraph_style or {}
    for style in (run_style, paragraph_style):
        _, weight = _weighted_font(style)
        if weight is not None and weight <= 300:
            return True
    if font_family:
        return is_light_font(font_family)
    return False


def slides_font_flags(bold: bool) -> int:
    return 16 if bold else 0


def _element_box(
    element: dict,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> tuple[float, float, float, float]:
    transform = element.get("transform", {})
    size = element.get("size", {})
    local_sx = (transform.get("scaleX") or 1) * scale_x
    local_sy = (transform.get("scaleY") or 1) * scale_y
    tx = offset_x + dimension_to_points({"magnitude": transform.get("translateX", 0), "unit": "EMU"}) * scale_x
    ty = offset_y + dimension_to_points({"magnitude": transform.get("translateY", 0), "unit": "EMU"}) * scale_y
    width = dimension_to_points(size.get("width")) * abs(local_sx)
    height = dimension_to_points(size.get("height")) * abs(local_sy)
    return (tx, ty, tx + width, ty + height)


def _collect_runs_from_text(
    text_content: dict,
    bbox: tuple[float, float, float, float],
    object_id: str,
    placeholder_type: str | None,
    theme_fonts: dict | None,
    spans: list[tuple[tuple[float, float, float, float], str, dict[str, Any]]],
) -> None:
    current_role = placeholder_type
    current_paragraph_style: dict = {}
    char_index = 0

    for text_element in text_content.get("textElements", []):
        if "paragraphMarker" in text_element:
            marker = text_element["paragraphMarker"]
            current_paragraph_style = marker.get("style", {})
            if "placeholder" in marker:
                current_role = marker["placeholder"].get("type", current_role)

        if "textRun" not in text_element:
            continue

        text_run = text_element["textRun"]
        content = text_run.get("content", "")
        stripped = content.strip()
        start_index = char_index
        end_index = char_index + len(content)
        char_index = end_index

        if not stripped:
            continue

        style = text_run.get("style", {})
        font_family = resolve_slides_font_family(
            style,
            current_paragraph_style,
            current_role or placeholder_type,
            theme_fonts,
        )
        font_size = resolve_slides_font_size(style, current_paragraph_style)
        bold = resolve_slides_bold(style, current_paragraph_style, font_family)
        light = resolve_slides_light(style, current_paragraph_style, font_family)
        flags = slides_font_flags(bold)

        from src.validators.color_utils import extract_rgb_from_slides_color

        color_hex = extract_rgb_from_slides_color(style.get("foregroundColor"))

        span_data: dict[str, Any] = {
            "font": font_family or "",
            "size": float(font_size) if font_size is not None else 0.0,
            "flags": flags,
            "bold": bold,
            "light": light,
            "color_hex": color_hex,
            "object_id": object_id,
            "text_range": {"start": start_index, "end": end_index},
        }
        spans.append((bbox, stripped, span_data))


def collect_slides_text_spans(
    slide: dict,
    theme_fonts: dict | None,
) -> list[tuple[tuple[float, float, float, float], str, dict[str, Any]]]:
    spans: list[tuple[tuple[float, float, float, float], str, dict[str, Any]]] = []

    def walk(
        elements: list[dict],
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        placeholder_type: str | None = None,
    ) -> None:
        for element in elements:
            transform = element.get("transform", {})
            local_sx = (transform.get("scaleX") or 1) * scale_x
            local_sy = (transform.get("scaleY") or 1) * scale_y
            child_offset_x = offset_x + dimension_to_points(
                {"magnitude": transform.get("translateX", 0), "unit": "EMU"}
            ) * scale_x
            child_offset_y = offset_y + dimension_to_points(
                {"magnitude": transform.get("translateY", 0), "unit": "EMU"}
            ) * scale_y

            if "elementGroup" in element:
                walk(
                    element["elementGroup"].get("children", []),
                    child_offset_x,
                    child_offset_y,
                    local_sx,
                    local_sy,
                    placeholder_type,
                )
                continue

            bbox = _element_box(element, offset_x, offset_y, scale_x, scale_y)
            object_id = element.get("objectId", "")

            ph_type = placeholder_type
            if "shape" in element:
                shape = element["shape"]
                if "placeholder" in shape:
                    ph_type = shape["placeholder"].get("type", ph_type)
                if "text" in shape:
                    _collect_runs_from_text(
                        shape["text"],
                        bbox,
                        object_id,
                        ph_type,
                        theme_fonts,
                        spans,
                    )

            if "table" in element:
                for row in element["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        if "text" in cell:
                            _collect_runs_from_text(
                                cell["text"],
                                bbox,
                                object_id,
                                ph_type,
                                theme_fonts,
                                spans,
                            )

    walk(slide.get("pageElements", []))
    return spans


def section_span_keys(section_slide) -> set[tuple[tuple[float, float, float, float], str]]:
    if not section_slide:
        return set()
    keys: set[tuple[tuple[float, float, float, float], str]] = {
        (section_slide.number.bbox, section_slide.number.text)
    }
    for title in section_slide.titles:
        keys.add((title.bbox, title.text))
    for subtitle in section_slide.subtitles:
        keys.add((subtitle.bbox, subtitle.text))
    return keys
