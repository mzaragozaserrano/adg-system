import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.brand_guidelines import ALLOWED_SLIDE_COLORS, TEXT_RULES
from src.validators import validate_pdf
from src.validators.rules import (
    expected_text_description,
    get_text_role,
    is_approved_font,
    resolve_slides_font_family,
    resolve_slides_font_size,
)
from src.validators.color_utils import (
    all_palette_color_options,
    describe_palette_color,
    nearest_palette_color,
    nearest_palette_colors,
    palette_violation_metadata,
    suggest_palette_color,
)
from src.validators.section_slides import detect_section_slide, validate_section_slide
from src.validators.slides_text import (
    collect_slides_text_spans,
    resolve_slides_bold,
    resolve_slides_light,
    styleable_text_range,
    utf16_len,
)
from src.validators.text_span_rules import TextSpanContext, validate_text_span
from src.validators.slides_validator import extract_presentation_id


def test_extract_presentation_id_from_url():
    url = "https://docs.google.com/presentation/d/abc123XYZ/edit"
    assert extract_presentation_id(url) == "abc123XYZ"


def test_extract_presentation_id_from_raw_id():
    assert extract_presentation_id("abc123XYZ") == "abc123XYZ"


def test_get_text_role_from_placeholder():
    assert get_text_role("TITLE", False, None) == "header"
    assert get_text_role("SUBTITLE", False, None) == "subtitle"
    assert get_text_role("BODY", False, None) == "body"


def test_get_text_role_from_size():
    assert get_text_role(None, False, 26) == "header"
    assert get_text_role(None, False, 14) == "subtitle"


def test_expected_text_description():
    assert "Bold" in expected_text_description("header")
    assert "Light" in expected_text_description("subtitle")
    assert TEXT_RULES["body"]["color"] == "#000000"


def test_is_approved_font_accepts_helvetica_variants():
    assert is_approved_font("Helvetica Neue")
    assert is_approved_font("Helvetica")
    assert is_approved_font("Helvetica-Bold")
    assert not is_approved_font("Arial")
    assert not is_approved_font(None)


def test_resolve_slides_font_family_from_paragraph_style():
    font = resolve_slides_font_family(
        run_style={},
        paragraph_style={"fontFamily": "Helvetica Neue"},
        placeholder_type="BODY",
        theme_fonts=None,
    )
    assert font == "Helvetica Neue"


def test_resolve_slides_font_family_from_theme():
    font = resolve_slides_font_family(
        run_style={},
        paragraph_style={},
        placeholder_type="TITLE",
        theme_fonts={"titleFontFamily": "Helvetica Neue", "bodyFontFamily": "Arial"},
    )
    assert font == "Helvetica Neue"


def test_resolve_slides_font_family_missing_does_not_assume_invalid():
    font = resolve_slides_font_family({}, {}, "BODY", None)
    assert font is None


def test_resolve_slides_font_size_from_run():
    size = resolve_slides_font_size(
        {"fontSize": {"magnitude": 26, "unit": "PT"}},
        {},
    )
    assert size == 26.0


def test_resolve_slides_font_size_from_paragraph():
    size = resolve_slides_font_size(
        {},
        {"fontSize": {"magnitude": 14, "unit": "PT"}},
    )
    assert size == 14.0


def test_resolve_slides_font_size_prefers_run_over_paragraph():
    size = resolve_slides_font_size(
        {"fontSize": {"magnitude": 26, "unit": "PT"}},
        {"fontSize": {"magnitude": 14, "unit": "PT"}},
    )
    assert size == 26.0


def test_resolve_slides_font_size_missing_returns_none():
    assert resolve_slides_font_size({}, {}) is None


def test_resolve_slides_bold_from_font_name():
    assert resolve_slides_bold({}, {}, "Helvetica Neue Bold") is True
    assert resolve_slides_bold({"bold": False}, {}, "Helvetica Neue Bold") is False


def test_resolve_slides_bold_from_weight():
    assert resolve_slides_bold(
        {"weightedFontFamily": {"fontFamily": "Helvetica Neue", "weight": 700}},
        {},
        "Helvetica Neue",
    ) is True


def test_resolve_slides_light_from_font_name():
    assert resolve_slides_light({}, {}, "Helvetica Neue Light") is True


def test_detect_section_slide_from_spans():
    bbox = (40.0, 40.0, 200.0, 200.0)
    raw_spans = [
        (
            bbox,
            "01.",
            {"font": "Helvetica Neue Bold", "size": 100.0, "flags": 16},
        ),
        (
            (40.0, 220.0, 500.0, 280.0),
            "INTRODUCCIÓN",
            {"font": "Helvetica Neue Bold", "size": 36.0, "flags": 16},
        ),
    ]
    section = detect_section_slide(raw_spans, 1, 720.0, 405.0)
    assert section is not None
    assert section.section_num == 1
    issues = validate_section_slide(section)
    assert not any(issue.category == "peso_fuente" for issue in issues)


def test_nearest_palette_color_for_gray():
    colors = nearest_palette_colors("#434343", 3)
    assert len(colors) == 3
    assert colors[0] in ALLOWED_SLIDE_COLORS


def test_nearest_palette_colors_for_mid_gray():
    colors = nearest_palette_colors("#5E5E5E", 3)
    assert colors[0] == "#6A96A6"
    assert len(colors) == 3


def test_nearest_palette_color_for_petrol_like():
    assert nearest_palette_color("#03465D") == "#02445B"


def test_suggest_palette_color_description():
    suggested, description = suggest_palette_color("#5E5E5E")
    assert suggested == "#6A96A6"
    assert description == "Acero Glaciar (#6A96A6)"


def test_all_palette_color_options_returns_full_palette():
    options = all_palette_color_options()
    assert len(options) == 8
    assert options[0]["color"] == "#02445B"
    assert any(item["color"] == "#000000" for item in options)


def test_palette_violation_metadata_includes_all_palette_colors():
    metadata = palette_violation_metadata("#5E5E5E")
    assert metadata["color_actual"] == "#5E5E5E"
    assert metadata["color_suggested"] == "#6A96A6"
    assert len(metadata["color_suggestions"]) == 8
    assert metadata["color_suggestions"][0]["color"] == "#02445B"
    assert any(item["color"] == "#000000" for item in metadata["color_suggestions"])


def test_styleable_text_range_excludes_trailing_newline():
    assert styleable_text_range("Hello\n", 0) == {"start": 0, "end": 5}
    assert styleable_text_range("Hello\n", 6) == {"start": 6, "end": 11}
    assert styleable_text_range("\n", 0) is None


def test_utf16_len_counts_emoji_as_google_slides():
    assert utf16_len("👍") == 2
    assert utf16_len("Hi") == 2


def test_collect_slides_text_spans_excludes_paragraph_newline():
    slide = {
        "pageElements": [
            {
                "objectId": "box1",
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0},
                "size": {
                    "width": {"magnitude": 100, "unit": "PT"},
                    "height": {"magnitude": 40, "unit": "PT"},
                },
                "shape": {
                    "text": {
                        "textElements": [
                            {"endIndex": 6, "paragraphMarker": {"style": {}}},
                            {
                                "endIndex": 6,
                                "textRun": {
                                    "content": "Hello\n",
                                    "style": {
                                        "fontFamily": "Arial",
                                        "fontSize": {"magnitude": 12, "unit": "PT"},
                                    },
                                },
                            },
                        ]
                    }
                },
            }
        ]
    }
    spans = collect_slides_text_spans(slide, None)
    assert len(spans) == 1
    assert spans[0][1] == "Hello"
    assert spans[0][2]["text_range"] == {"start": 0, "end": 5}
    assert spans[0][2]["font"] == "Arial"


def test_collect_slides_text_spans_second_paragraph_uses_api_start_index():
    slide = {
        "pageElements": [
            {
                "objectId": "box1",
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0},
                "size": {
                    "width": {"magnitude": 100, "unit": "PT"},
                    "height": {"magnitude": 40, "unit": "PT"},
                },
                "shape": {
                    "text": {
                        "textElements": [
                            {"endIndex": 6, "paragraphMarker": {"style": {}}},
                            {
                                "endIndex": 6,
                                "textRun": {
                                    "content": "Hello\n",
                                    "style": {
                                        "fontFamily": "Arial",
                                        "fontSize": {"magnitude": 12, "unit": "PT"},
                                    },
                                },
                            },
                            {"startIndex": 6, "endIndex": 12, "paragraphMarker": {"style": {}}},
                            {
                                "startIndex": 6,
                                "endIndex": 12,
                                "textRun": {
                                    "content": "World\n",
                                    "style": {
                                        "fontFamily": "Arial",
                                        "fontSize": {"magnitude": 12, "unit": "PT"},
                                    },
                                },
                            },
                        ]
                    }
                },
            }
        ]
    }
    spans = collect_slides_text_spans(slide, None)
    assert [span[2]["text_range"] for span in spans] == [
        {"start": 0, "end": 5},
        {"start": 6, "end": 11},
    ]


def test_collect_slides_text_spans_includes_table_cell_location():
    slide = {
        "pageElements": [
            {
                "objectId": "table1",
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0},
                "size": {
                    "width": {"magnitude": 200, "unit": "PT"},
                    "height": {"magnitude": 80, "unit": "PT"},
                },
                "table": {
                    "tableRows": [
                        {
                            "tableCells": [
                                {
                                    "text": {
                                        "textElements": [
                                            {"endIndex": 6, "paragraphMarker": {"style": {}}},
                                            {
                                                "endIndex": 6,
                                                "textRun": {
                                                    "content": "Celta\n",
                                                    "style": {
                                                        "fontFamily": "Arial",
                                                        "fontSize": {"magnitude": 12, "unit": "PT"},
                                                    },
                                                },
                                            },
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                },
            }
        ]
    }
    spans = collect_slides_text_spans(slide, None)
    assert spans[0][2]["text_range"] == {
        "start": 0,
        "end": 5,
        "rowIndex": 0,
        "columnIndex": 0,
    }


def _make_ctx(**kwargs) -> TextSpanContext:
    defaults = dict(
        slide_number=1,
        text="Texto de prueba",
        bbox=(10.0, 10.0, 200.0, 30.0),
        page_width=720.0,
        page_height=405.0,
        font="Helvetica Neue",
        size=14.0,
        flags=0,
        color_hex="#01222E",
        location="superior-izquierda",
    )
    defaults.update(kwargs)
    return TextSpanContext(**defaults)


def test_body_placeholder_skips_header_subtitle_check():
    ctx = _make_ctx(
        size=14.0,
        placeholder_type="BODY",
        bbox=(10.0, 80.0, 600.0, 100.0),
    )
    issues = validate_text_span(ctx)
    header_issues = [i for i in issues if "subtítulo" in i.message.lower() or "título" in i.message.lower()]
    assert not header_issues, "Texto en placeholder BODY no debe generar errores de título/subtítulo"


def test_subtitle_placeholder_validates_regardless_of_position():
    ctx = _make_ctx(
        size=14.0,
        font="Helvetica Neue",
        color_hex="#FF0000",
        placeholder_type="SUBTITLE",
        bbox=(10.0, 300.0, 400.0, 320.0),
    )
    issues = validate_text_span(ctx)
    color_issues = [i for i in issues if i.category == "color"]
    assert color_issues, "Texto en placeholder SUBTITLE fuera de posición debe validar color"


def test_body_placeholder_still_validates_font():
    ctx = _make_ctx(
        font="Arial",
        placeholder_type="BODY",
        bbox=(10.0, 100.0, 600.0, 120.0),
    )
    issues = validate_text_span(ctx)
    font_issues = [i for i in issues if i.category == "tipografía"]
    assert font_issues, "Texto en placeholder BODY con fuente no ADG debe seguir detectándose"


def test_free_text_top_left_still_validates():
    ctx = _make_ctx(
        size=14.0,
        font="Helvetica Neue",
        color_hex="#FF0000",
        placeholder_type=None,
        bbox=(10.0, 50.0, 300.0, 70.0),
    )
    issues = validate_text_span(ctx)
    color_issues = [i for i in issues if i.category == "color"]
    assert color_issues, "Texto libre en zona superior-izquierda debe validar color de subtítulo"


def test_free_text_bottom_does_not_validate_as_subtitle():
    ctx = _make_ctx(
        size=14.0,
        font="Helvetica Neue",
        color_hex="#FF0000",
        placeholder_type=None,
        bbox=(10.0, 350.0, 300.0, 370.0),
    )
    issues = validate_text_span(ctx)
    header_issues = [i for i in issues if "subtítulo" in i.message.lower() or "título" in i.message.lower()]
    assert not header_issues, "Texto libre en zona inferior no debe validarse como título/subtítulo"


def test_collect_slides_text_spans_stores_placeholder_type():
    slide = {
        "pageElements": [
            {
                "objectId": "body1",
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0},
                "size": {
                    "width": {"magnitude": 400, "unit": "PT"},
                    "height": {"magnitude": 200, "unit": "PT"},
                },
                "shape": {
                    "placeholder": {"type": "BODY"},
                    "text": {
                        "textElements": [
                            {"endIndex": 7, "paragraphMarker": {"style": {}}},
                            {
                                "endIndex": 7,
                                "textRun": {
                                    "content": "Texto\n",
                                    "style": {
                                        "fontFamily": "Helvetica Neue",
                                        "fontSize": {"magnitude": 14, "unit": "PT"},
                                    },
                                },
                            },
                        ]
                    },
                },
            }
        ]
    }
    spans = collect_slides_text_spans(slide, None)
    assert spans[0][2]["placeholder_type"] == "BODY"


def test_validate_sample_pdf():
    sample = Path(__file__).resolve().parent.parent / "docs" / "samples" / "plantilla_base_adg.pdf"
    if not sample.exists():
        pytest.skip("PDF de muestra no disponible")
    result = validate_pdf(sample)
    assert result.total_slides > 0
    assert result.source_type == "pdf"
