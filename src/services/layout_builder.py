from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

from config.brand_guidelines import (
    BRAND_FONT,
    SUBTITLE_COLOR,
    SUBTITLE_FONT_SIZE,
    TITLE_COLOR,
    TITLE_FONT_SIZE,
)
from config.settings import settings
from src.integrations.google.clients import build_drive_client, build_slides_client
from src.services.block_classifier import (
    BlockRole,
    ClassifiedBlock,
    classify_content_slide,
    classify_cover_slide,
    infer_cover_title_from_filename,
)
from src.services.content_mapper import (
    build_replace_requests,
    map_cover_to_slots,
)
from src.services.ocr_blocks import OcrBlock, ocr_image_bytes_drive, ocr_image_bytes_structured
from src.services.slide_images import (
    download_drive_pdf,
    pdf_bytes_to_page_images,
    pdf_bytes_to_page_jpegs,
    slides_to_page_images,
    upload_pdf_bytes,
)
from src.services.template_analyzer import analyze_template_slide
from src.validators.slides_text import collect_slides_text_spans

PT_TO_EMU = 914400 / 72
SLIDE_W_PT = 720.0
SLIDE_H_PT = 405.0

MARGIN_LEFT_PT = 36.0
MARGIN_TOP_PT = 20.0
CONTENT_W_PT = SLIDE_W_PT - MARGIN_LEFT_PT * 2
TITLE_H_PT = 40.0
SUBTITLE_H_PT = 24.0
BODY_Y_PT = MARGIN_TOP_PT + TITLE_H_PT + SUBTITLE_H_PT + 6.0
BODY_H_PT = SLIDE_H_PT - BODY_Y_PT - MARGIN_TOP_PT


def _pt(value: float) -> dict:
    return {"magnitude": value, "unit": "PT"}


def _color_rgb(hex_color: str) -> dict:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


def _text_box_request(
    object_id: str,
    page_id: str,
    text: str,
    x_pt: float,
    y_pt: float,
    w_pt: float,
    h_pt: float,
    font_size: float,
    color_hex: str,
    bold: bool = False,
    light: bool = False,
) -> list[dict]:
    weight = 300 if light else (700 if bold else 400)
    return [
        {
            "createShape": {
                "objectId": object_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": page_id,
                    "size": {
                        "width": _pt(w_pt),
                        "height": _pt(h_pt),
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": x_pt * PT_TO_EMU,
                        "translateY": y_pt * PT_TO_EMU,
                        "unit": "EMU",
                    },
                },
            }
        },
        {
            "insertText": {
                "objectId": object_id,
                "insertionIndex": 0,
                "text": text,
            }
        },
        {
            "updateTextStyle": {
                "objectId": object_id,
                "style": {
                    "fontFamily": BRAND_FONT,
                    "fontSize": _pt(font_size),
                    "foregroundColor": {
                        "opaqueColor": {"rgbColor": _color_rgb(color_hex)}
                    },
                    "bold": bold,
                    "weightedFontFamily": {
                        "fontFamily": BRAND_FONT,
                        "weight": weight,
                    },
                },
                "fields": "fontFamily,fontSize,foregroundColor,bold,weightedFontFamily",
            }
        },
    ]


def _build_content_slide_requests(
    page_id: str,
    classified: list[ClassifiedBlock],
    slide_index: int,
) -> list[dict]:
    requests: list[dict] = []

    title_text = ""
    subtitle_text = ""
    body_parts: list[str] = []
    section_num = ""
    section_title = ""

    for cb in classified:
        text = cb.block.text.strip()
        if not text:
            continue
        if cb.role == BlockRole.SLIDE_TITLE:
            title_text = text
        elif cb.role == BlockRole.SLIDE_SUBTITLE:
            subtitle_text = text
        elif cb.role == BlockRole.SECTION_NUMBER:
            section_num = text
        elif cb.role == BlockRole.SECTION_TITLE:
            section_title = text
        elif cb.role == BlockRole.BODY:
            body_parts.append(text)

    is_section = bool(section_num)
    prefix = f"s{slide_index}"

    if is_section:
        if section_num:
            requests.extend(
                _text_box_request(
                    object_id=f"{prefix}_secnum",
                    page_id=page_id,
                    text=section_num,
                    x_pt=SLIDE_W_PT / 2 - 40,
                    y_pt=60.0,
                    w_pt=80.0,
                    h_pt=100.0,
                    font_size=80.0,
                    color_hex=TITLE_COLOR,
                    bold=True,
                )
            )
        if section_title:
            requests.extend(
                _text_box_request(
                    object_id=f"{prefix}_sectitle",
                    page_id=page_id,
                    text=section_title,
                    x_pt=MARGIN_LEFT_PT,
                    y_pt=180.0,
                    w_pt=CONTENT_W_PT,
                    h_pt=60.0,
                    font_size=TITLE_FONT_SIZE,
                    color_hex=TITLE_COLOR,
                    bold=True,
                )
            )
    else:
        if title_text:
            requests.extend(
                _text_box_request(
                    object_id=f"{prefix}_title",
                    page_id=page_id,
                    text=title_text,
                    x_pt=MARGIN_LEFT_PT,
                    y_pt=MARGIN_TOP_PT,
                    w_pt=CONTENT_W_PT,
                    h_pt=TITLE_H_PT,
                    font_size=TITLE_FONT_SIZE,
                    color_hex=TITLE_COLOR,
                    bold=True,
                )
            )
        if subtitle_text:
            requests.extend(
                _text_box_request(
                    object_id=f"{prefix}_subtitle",
                    page_id=page_id,
                    text=subtitle_text,
                    x_pt=MARGIN_LEFT_PT,
                    y_pt=MARGIN_TOP_PT + TITLE_H_PT + 4,
                    w_pt=CONTENT_W_PT,
                    h_pt=SUBTITLE_H_PT,
                    font_size=SUBTITLE_FONT_SIZE,
                    color_hex=SUBTITLE_COLOR,
                    light=True,
                )
            )
        if body_parts:
            requests.extend(
                _text_box_request(
                    object_id=f"{prefix}_body",
                    page_id=page_id,
                    text="\n".join(body_parts),
                    x_pt=MARGIN_LEFT_PT,
                    y_pt=BODY_Y_PT,
                    w_pt=CONTENT_W_PT,
                    h_pt=BODY_H_PT,
                    font_size=12.0,
                    color_hex="#000000",
                )
            )

        if not title_text and not body_parts:
            requests.extend(
                _text_box_request(
                    object_id=f"{prefix}_empty",
                    page_id=page_id,
                    text=" ",
                    x_pt=MARGIN_LEFT_PT,
                    y_pt=MARGIN_TOP_PT,
                    w_pt=CONTENT_W_PT,
                    h_pt=TITLE_H_PT,
                    font_size=TITLE_FONT_SIZE,
                    color_hex=TITLE_COLOR,
                    bold=True,
                )
            )

    return requests


@dataclass
class LayoutResult:
    presentation_url: str
    presentation_id: str
    slides_processed: int
    skipped_slides: list[int] = field(default_factory=list)
    cover_title: str = ""
    cover_subtitle: str = ""


def _ocr_page(image_bytes: bytes, drive_service=None) -> list[OcrBlock]:
    if not image_bytes:
        logger.warning("_ocr_page: imagen vacía, se omite OCR")
        return []

    try:
        blocks = ocr_image_bytes_structured(image_bytes)
        logger.info("_ocr_page: Vision API — %d bloques (%d bytes)", len(blocks), len(image_bytes))
        return blocks
    except Exception as exc:
        logger.warning("_ocr_page: Vision API falló (%s), probando Drive OCR", exc)

    if drive_service is not None:
        try:
            blocks = ocr_image_bytes_drive(image_bytes, drive_service)
            logger.info("_ocr_page: Drive OCR — %d bloques", len(blocks))
            return blocks
        except Exception as exc:
            logger.error("_ocr_page: Drive OCR también falló: %s", exc)

    return []


def _detect_cover_text(
    page_images: list[bytes],
    filename: str,
    title_override: str,
    subtitle_override: str,
    drive_service=None,
) -> tuple[str, str, list[ClassifiedBlock]]:
    cover_title = title_override
    cover_subtitle = subtitle_override
    classified: list[ClassifiedBlock] = []

    if page_images:
        cover_blocks = _ocr_page(page_images[0], drive_service=drive_service)
        if cover_blocks:
            img_w, img_h = 1024.0, 576.0
            classified = classify_cover_slide(cover_blocks, img_w, img_h)
            for cb in classified:
                text = cb.block.text.strip()
                if cb.role == BlockRole.COVER_TITLE and not cover_title:
                    cover_title = text
                elif cb.role == BlockRole.COVER_SUBTITLE and not cover_subtitle:
                    cover_subtitle = text

    if not cover_title:
        cover_title = infer_cover_title_from_filename(filename)

    return cover_title, cover_subtitle, classified


def _fill_cover_from_template(
    slides_service,
    new_id: str,
    cover_slide: dict,
    classified_cover: list[ClassifiedBlock],
    cover_title: str,
    cover_subtitle: str,
) -> None:
    theme_fonts: dict | None = None
    slots = analyze_template_slide(cover_slide, theme_fonts)

    if not slots:
        return

    mapping = map_cover_to_slots(
        classified_cover,
        slots,
        filename_fallback=cover_title,
    )

    if not mapping:
        return

    replace_reqs = build_replace_requests(mapping)
    if replace_reqs:
        slides_service.presentations().batchUpdate(
            presentationId=new_id,
            body={"requests": replace_reqs},
        ).execute()


def _get_blank_layout_id(presentation: dict) -> str | None:
    for layout in presentation.get("layouts", []):
        name = (layout.get("layoutProperties") or {}).get("name", "").upper()
        display = (layout.get("layoutProperties") or {}).get("displayName", "").upper()
        if "BLANK" in name or "BLANK" in display or name == "" or display == "":
            return layout.get("objectId")
    layouts = presentation.get("layouts", [])
    if layouts:
        return layouts[-1].get("objectId")
    return None


def _add_blank_slide(
    slides_service,
    presentation_id: str,
    insertion_index: int,
    layout_id: str | None,
) -> tuple[str | None, str]:
    """Devuelve (objectId, error_msg). error_msg vacío si tuvo éxito."""
    slide_id = f"slide_{uuid.uuid4().hex[:16]}"

    attempts: list[dict] = []
    if layout_id:
        attempts.append({
            "createSlide": {
                "objectId": slide_id,
                "insertionIndex": insertion_index,
                "slideLayoutReference": {"layoutId": layout_id},
            }
        })
    attempts += [
        {
            "createSlide": {
                "objectId": slide_id,
                "insertionIndex": insertion_index,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }
        },
        {
            "createSlide": {
                "objectId": slide_id,
                "insertionIndex": insertion_index,
            }
        },
    ]

    last_error = ""
    for attempt in attempts:
        try:
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": [attempt]},
            ).execute()
            return slide_id, ""
        except Exception as exc:
            last_error = str(exc)
            logger.warning("createSlide falló (idx=%d): %s", insertion_index, exc)

    logger.error(
        "No se pudo crear diapositiva en índice %d para presentación %s: %s",
        insertion_index,
        presentation_id,
        last_error,
    )
    return None, last_error


def _init_from_template(
    drive_service,
    slides_service,
    template_id: str,
    name: str,
    cover_title: str,
    cover_subtitle: str,
    classified_cover: list[ClassifiedBlock],
) -> tuple[str, int, str | None]:
    copy = drive_service.files().copy(
        fileId=template_id,
        body={"name": name},
    ).execute()
    new_id = copy["id"]

    pres = slides_service.presentations().get(presentationId=new_id).execute()
    slides = pres.get("slides", [])
    layout_id = _get_blank_layout_id(pres)

    if len(slides) > 2:
        to_delete = [slides[i]["objectId"] for i in range(1, len(slides) - 1)]
        delete_requests = [
            {"deleteObject": {"objectId": oid}} for oid in reversed(to_delete)
        ]
        slides_service.presentations().batchUpdate(
            presentationId=new_id,
            body={"requests": delete_requests},
        ).execute()
        pres = slides_service.presentations().get(presentationId=new_id).execute()
        slides = pres.get("slides", [])

    if slides:
        _fill_cover_from_template(
            slides_service,
            new_id,
            slides[0],
            classified_cover,
            cover_title,
            cover_subtitle,
        )

    return new_id, 1, layout_id


def _init_blank_presentation(
    slides_service,
    name: str,
    cover_title: str,
    cover_subtitle: str,
) -> tuple[str, int, None]:
    new_pres = slides_service.presentations().create(
        body={"title": name}
    ).execute()
    new_id = new_pres["presentationId"]
    first_slide_id = new_pres.get("slides", [{}])[0].get("objectId")

    init_requests: list[dict] = []
    if first_slide_id:
        if cover_title:
            init_requests.extend(
                _text_box_request(
                    object_id="cover_title_box",
                    page_id=first_slide_id,
                    text=cover_title,
                    x_pt=MARGIN_LEFT_PT,
                    y_pt=SLIDE_H_PT / 2 - 50,
                    w_pt=CONTENT_W_PT,
                    h_pt=60.0,
                    font_size=32.0,
                    color_hex=TITLE_COLOR,
                    bold=True,
                )
            )
        if cover_subtitle:
            init_requests.extend(
                _text_box_request(
                    object_id="cover_subtitle_box",
                    page_id=first_slide_id,
                    text=cover_subtitle,
                    x_pt=MARGIN_LEFT_PT,
                    y_pt=SLIDE_H_PT / 2 + 20,
                    w_pt=CONTENT_W_PT,
                    h_pt=30.0,
                    font_size=SUBTITLE_FONT_SIZE,
                    color_hex=SUBTITLE_COLOR,
                    light=True,
                )
            )

    if init_requests:
        slides_service.presentations().batchUpdate(
            presentationId=new_id,
            body={"requests": init_requests},
        ).execute()

    return new_id, 1, None


def build_layout(
    source_id: str,
    source_type: str,
    filename: str,
    credentials: Credentials,
    title_override: str = "",
    subtitle_override: str = "",
    pdf_bytes_direct: bytes | None = None,
) -> LayoutResult:
    slides_service = build_slides_client(credentials)
    drive_service = build_drive_client(credentials)

    is_pdf = pdf_bytes_direct is not None or source_type == "pdf"

    if pdf_bytes_direct is not None:
        pdf_bytes_for_ocr: bytes | None = pdf_bytes_direct
        page_images = pdf_bytes_to_page_jpegs(pdf_bytes_direct)
    elif source_type == "pdf":
        pdf_bytes_raw = download_drive_pdf(source_id, credentials)
        pdf_bytes_for_ocr = pdf_bytes_raw
        page_images = pdf_bytes_to_page_jpegs(pdf_bytes_raw)
    else:
        pdf_bytes_for_ocr = None
        page_images = slides_to_page_images(source_id, credentials)

    if not page_images:
        raise ValueError("No se pudieron obtener imágenes del documento fuente")

    safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    doc_name = f"{safe_name} — Maqueta ADG"

    cover_title, cover_subtitle, classified_cover = _detect_cover_text(
        page_images, filename, title_override, subtitle_override,
        drive_service=drive_service,
    )

    template_id = settings.layout_template_slides_id
    if template_id:
        new_id, content_insert_index, layout_id = _init_from_template(
            drive_service,
            slides_service,
            template_id,
            doc_name,
            cover_title,
            cover_subtitle,
            classified_cover,
        )
    else:
        new_id, content_insert_index, layout_id = _init_blank_presentation(
            slides_service,
            doc_name,
            cover_title,
            cover_subtitle,
        )

    content_pages = page_images[1:]
    skipped: list[int] = []
    first_add_slide_error: str = ""

    logger.info(
        "build_layout: %d páginas de contenido a procesar (insert_index=%d, layout_id=%s)",
        len(content_pages), content_insert_index, layout_id,
    )

    for idx, img_bytes in enumerate(content_pages):
        slide_number = idx + 2
        insertion_index = content_insert_index + idx

        page_id, err = _add_blank_slide(slides_service, new_id, insertion_index, layout_id)

        if not page_id:
            if not first_add_slide_error:
                first_add_slide_error = err
            logger.error("Slide %d: _add_blank_slide devolvió None: %s", slide_number, err)
            skipped.append(slide_number)
            continue

        logger.info("Slide %d: creada con page_id=%s", slide_number, page_id)

        blocks = _ocr_page(img_bytes, drive_service=drive_service)

        img_w, img_h = 1024.0, 576.0
        classified = classify_content_slide(blocks, img_w, img_h) if blocks else []

        content_requests = _build_content_slide_requests(page_id, classified, idx)
        if content_requests:
            try:
                slides_service.presentations().batchUpdate(
                    presentationId=new_id,
                    body={"requests": content_requests},
                ).execute()
                logger.info("Slide %d: %d requests aplicados", slide_number, len(content_requests))
            except Exception as exc:
                logger.error("Slide %d: error al aplicar contenido: %s", slide_number, exc)

    if first_add_slide_error and len(skipped) == len(content_pages):
        raise RuntimeError(
            f"createSlide falló en todas las diapositivas de contenido. "
            f"Primer error: {first_add_slide_error}"
        )

    url = f"https://docs.google.com/presentation/d/{new_id}/edit"
    current_pres = slides_service.presentations().get(presentationId=new_id).execute()
    slides_processed = len(current_pres.get("slides", []))

    return LayoutResult(
        presentation_url=url,
        presentation_id=new_id,
        slides_processed=slides_processed,
        skipped_slides=skipped,
        cover_title=cover_title,
        cover_subtitle=cover_subtitle,
    )
