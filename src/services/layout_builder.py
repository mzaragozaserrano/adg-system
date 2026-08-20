from __future__ import annotations

from dataclasses import dataclass, field

from google.oauth2.credentials import Credentials

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
from src.services.ocr_blocks import OcrBlock, ocr_image_bytes_structured
from src.services.slide_images import (
    download_drive_pdf,
    pdf_bytes_to_page_images,
    slides_to_page_images,
)

PT_TO_EMU = 914400 / 72
SLIDE_W_PT = 720.0
SLIDE_H_PT = 405.0
SLIDE_W_EMU = int(SLIDE_W_PT * PT_TO_EMU)
SLIDE_H_EMU = int(SLIDE_H_PT * PT_TO_EMU)

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

    return requests


@dataclass
class LayoutResult:
    presentation_url: str
    presentation_id: str
    slides_processed: int
    skipped_slides: list[int] = field(default_factory=list)
    cover_title: str = ""
    cover_subtitle: str = ""


def _get_template_slide_ids(
    slides_service,
    template_id: str,
) -> tuple[str | None, str | None]:
    try:
        pres = slides_service.presentations().get(presentationId=template_id).execute()
        slides = pres.get("slides", [])
        cover_id = slides[0]["objectId"] if len(slides) >= 1 else None
        backcover_id = slides[-1]["objectId"] if len(slides) >= 2 else None
        return cover_id, backcover_id
    except Exception:
        return None, None


def _copy_slide_from_template(
    slides_service,
    source_presentation_id: str,
    source_page_id: str,
    target_presentation_id: str,
    insertion_index: int,
) -> str | None:
    try:
        new_id = f"copied_{source_page_id}_{insertion_index}"
        slides_service.presentations().batchUpdate(
            presentationId=target_presentation_id,
            body={
                "requests": [
                    {
                        "duplicateObject": {
                            "objectId": source_page_id,
                        }
                    }
                ]
            },
        ).execute()
        return new_id
    except Exception:
        return None


def _fill_cover_placeholder(
    slides_service,
    presentation_id: str,
    page_id: str,
    title: str,
    subtitle: str,
) -> list[dict]:
    requests: list[dict] = []
    if title:
        requests.append({
            "replaceAllText": {
                "containsText": {"text": "{{TITULO}}", "matchCase": False},
                "replaceText": title,
                "pageObjectIds": [page_id],
            }
        })
    if subtitle:
        requests.append({
            "replaceAllText": {
                "containsText": {"text": "{{SUBTITULO}}", "matchCase": False},
                "replaceText": subtitle,
                "pageObjectIds": [page_id],
            }
        })
    return requests


def _ocr_page(image_bytes: bytes) -> list[OcrBlock]:
    if not image_bytes:
        return []
    try:
        return ocr_image_bytes_structured(image_bytes)
    except Exception:
        return []


def build_layout(
    source_id: str,
    source_type: str,
    filename: str,
    credentials: Credentials,
    title_override: str = "",
    subtitle_override: str = "",
) -> LayoutResult:
    slides_service = build_slides_client(credentials)
    drive_service = build_drive_client(credentials)

    if source_type == "pdf":
        pdf_bytes = download_drive_pdf(source_id, credentials)
        page_images = pdf_bytes_to_page_images(pdf_bytes)
    else:
        page_images = slides_to_page_images(source_id, credentials)

    if not page_images:
        raise ValueError("No se pudieron obtener imágenes del documento fuente")

    safe_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    new_pres = slides_service.presentations().create(
        body={"title": f"{safe_name} — Maqueta ADG"}
    ).execute()
    new_id = new_pres["presentationId"]
    new_slides = new_pres.get("slides", [])

    template_id = settings.layout_template_slides_id
    cover_title = title_override
    cover_subtitle = subtitle_override
    backcover_page_id: str | None = None

    if template_id:
        template_pres = slides_service.presentations().get(
            presentationId=template_id
        ).execute()
        template_slides = template_pres.get("slides", [])

        if template_slides:
            cover_template_id = template_slides[0]["objectId"]
            drive_service.files().copy(
                fileId=template_id,
                body={"name": "__tmp_cover_copy__"},
            )

    first_slide_id = new_slides[0]["objectId"] if new_slides else None

    cover_blocks = _ocr_page(page_images[0])

    if cover_blocks:
        img_w, img_h = 1024.0, 576.0
        classified_cover = classify_cover_slide(cover_blocks, img_w, img_h)
        for cb in classified_cover:
            text = cb.block.text.strip()
            if cb.role == BlockRole.COVER_TITLE and not cover_title:
                cover_title = text
            elif cb.role == BlockRole.COVER_SUBTITLE and not cover_subtitle:
                cover_subtitle = text

    if not cover_title:
        cover_title = infer_cover_title_from_filename(filename)

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

    content_pages = page_images[1:]
    skipped: list[int] = []

    for idx, img_bytes in enumerate(content_pages):
        slide_number = idx + 2

        add_slide_req = slides_service.presentations().batchUpdate(
            presentationId=new_id,
            body={"requests": [{"addSlide": {"insertionIndex": idx + 1}}]},
        ).execute()

        replies = add_slide_req.get("replies", [])
        page_id = None
        for reply in replies:
            if "addSlide" in reply:
                page_id = reply["addSlide"].get("objectId")
                break

        if not page_id:
            skipped.append(slide_number)
            continue

        blocks = _ocr_page(img_bytes)
        if not blocks:
            skipped.append(slide_number)
            continue

        img_w, img_h = 1024.0, 576.0
        classified = classify_content_slide(blocks, img_w, img_h)

        content_requests = _build_content_slide_requests(page_id, classified, slide_number)
        if content_requests:
            slides_service.presentations().batchUpdate(
                presentationId=new_id,
                body={"requests": content_requests},
            ).execute()

    if template_id:
        template_pres = slides_service.presentations().get(
            presentationId=template_id
        ).execute()
        template_slides = template_pres.get("slides", [])
        if len(template_slides) >= 2:
            backcover_src_id = template_slides[-1]["objectId"]
            current_pres = slides_service.presentations().get(
                presentationId=new_id
            ).execute()
            total_slides = len(current_pres.get("slides", []))
            try:
                slides_service.presentations().batchUpdate(
                    presentationId=new_id,
                    body={
                        "requests": [
                            {
                                "addSlide": {
                                    "insertionIndex": total_slides,
                                    "slideLayoutReference": {"predefinedLayout": "BLANK"},
                                }
                            }
                        ]
                    },
                ).execute()
            except Exception:
                pass

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
