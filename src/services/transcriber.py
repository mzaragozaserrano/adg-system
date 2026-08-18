from __future__ import annotations

import json
import os
import tempfile

import httpx
from google.cloud import vision
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.services.presentation_cache import get_cached_presentation


_vision_client: vision.ImageAnnotatorClient | None = None


def _get_vision_client() -> vision.ImageAnnotatorClient:
    global _vision_client
    if _vision_client is None:
        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if sa_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, prefix="adg_sa_"
            )
            tmp.write(sa_json)
            tmp.flush()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client


def _collect_images(slide: dict) -> list[dict]:
    results: list[dict] = []

    def walk(elements: list[dict]) -> None:
        for el in elements:
            if "elementGroup" in el:
                walk(el["elementGroup"].get("children", []))
            elif "image" in el:
                results.append({
                    "object_id": el.get("objectId"),
                    "content_url": el["image"].get("contentUrl"),
                    "size": el.get("size"),
                    "transform": el.get("transform"),
                })

    walk(slide.get("pageElements", []))
    return results


def _ocr_image_url(content_url: str) -> str:
    response = httpx.get(content_url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    image_bytes = response.content

    client = _get_vision_client()
    image = vision.Image(content=image_bytes)
    result = client.text_detection(image=image)
    texts = result.text_annotations
    if texts:
        return texts[0].description.strip()
    return ""


def _emu_to_pt(value: float | None) -> float:
    if value is None:
        return 0.0
    return value / 914400 * 72


def _build_replace_requests(
    page_id: str,
    image_object_id: str,
    text: str,
    size: dict | None,
    transform: dict | None,
) -> list[dict]:
    width_emu = (size or {}).get("width", {}).get("magnitude", 3000000)
    height_emu = (size or {}).get("height", {}).get("magnitude", 1700000)
    tx = (transform or {}).get("translateX", 0)
    ty = (transform or {}).get("translateY", 0)
    scale_x = (transform or {}).get("scaleX", 1.0)
    scale_y = (transform or {}).get("scaleY", 1.0)

    new_box_id = f"transcribed_{image_object_id}"

    return [
        {
            "createShape": {
                "objectId": new_box_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": page_id,
                    "size": {
                        "width": {"magnitude": width_emu * scale_x, "unit": "EMU"},
                        "height": {"magnitude": height_emu * scale_y, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": tx,
                        "translateY": ty,
                        "unit": "EMU",
                    },
                },
            }
        },
        {
            "insertText": {
                "objectId": new_box_id,
                "insertionIndex": 0,
                "text": text,
            }
        },
        {
            "updateTextStyle": {
                "objectId": new_box_id,
                "style": {
                    "fontFamily": "Helvetica Neue",
                    "foregroundColor": {
                        "opaqueColor": {
                            "rgbColor": {"red": 0, "green": 0, "blue": 0}
                        }
                    },
                },
                "fields": "fontFamily,foregroundColor",
            }
        },
        {
            "deleteObject": {
                "objectId": image_object_id,
            }
        },
    ]


def transcribe_slides(
    presentation_id: str,
    slide_numbers: list[int],
    new_document: bool,
    credentials: Credentials,
    min_words: int = 5,
) -> dict:
    slides_service = build("slides", "v1", credentials=credentials)
    drive_service = build("drive", "v3", credentials=credentials)

    presentation = get_cached_presentation(slides_service, presentation_id)
    slides = presentation.get("slides", [])
    total = len(slides)

    indices = sorted({n - 1 for n in slide_numbers if 1 <= n <= total})
    if not indices:
        return {
            "transcribed_slides": [],
            "skipped_slides": [],
            "presentation_url": None,
            "new_document": new_document,
        }

    if new_document:
        source_meta = drive_service.files().get(fileId=presentation_id, fields="name").execute()
        copy_name = f"{source_meta.get('name', 'Presentación')} (Transcrita)"
        copy = drive_service.files().copy(
            fileId=presentation_id,
            body={"name": copy_name},
        ).execute()
        target_id = copy["id"]

        target_pres = slides_service.presentations().get(presentationId=target_id).execute()
        target_slides = target_pres.get("slides", [])

        keep_indices = set(indices)
        ids_to_delete = [
            target_slides[i]["objectId"]
            for i in range(len(target_slides))
            if i not in keep_indices
        ]
        if ids_to_delete:
            delete_requests = [{"deleteObject": {"objectId": oid}} for oid in reversed(ids_to_delete)]
            slides_service.presentations().batchUpdate(
                presentationId=target_id,
                body={"requests": delete_requests},
            ).execute()

        target_pres = slides_service.presentations().get(presentationId=target_id).execute()
        target_slides = target_pres.get("slides", [])
        work_indices = list(range(len(target_slides)))
    else:
        target_id = presentation_id
        target_slides = slides
        work_indices = indices

    transcribed: list[int] = []
    skipped: list[int] = []
    all_requests: list[dict] = []

    for work_idx in work_indices:
        if work_idx >= len(target_slides):
            continue

        slide = target_slides[work_idx]
        page_id = slide.get("objectId")
        original_number = indices[work_indices.index(work_idx)] + 1 if new_document else work_idx + 1
        images = _collect_images(slide)

        slide_had_text = False
        for img in images:
            if not img["content_url"]:
                continue
            try:
                text = _ocr_image_url(img["content_url"])
            except Exception:
                continue

            word_count = len(text.split())
            if word_count < min_words:
                continue

            reqs = _build_replace_requests(
                page_id,
                img["object_id"],
                text,
                img["size"],
                img["transform"],
            )
            all_requests.extend(reqs)
            slide_had_text = True

        if slide_had_text:
            transcribed.append(original_number)
        else:
            skipped.append(original_number)

    if all_requests:
        slides_service.presentations().batchUpdate(
            presentationId=target_id,
            body={"requests": all_requests},
        ).execute()

    return {
        "transcribed_slides": transcribed,
        "skipped_slides": skipped,
        "presentation_url": f"https://docs.google.com/presentation/d/{target_id}/edit",
        "new_document": new_document,
    }
