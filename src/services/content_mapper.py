from __future__ import annotations

from src.services.block_classifier import BlockRole, ClassifiedBlock
from src.services.template_analyzer import TemplateSlot


def map_cover_to_slots(
    classified: list[ClassifiedBlock],
    slots: list[TemplateSlot],
    filename_fallback: str = "",
) -> dict[str, str]:
    title_text = ""
    subtitle_text = ""

    for cb in classified:
        text = cb.block.text.strip()
        if not text:
            continue
        if cb.role == BlockRole.COVER_TITLE and not title_text:
            title_text = text
        elif cb.role == BlockRole.COVER_SUBTITLE and not subtitle_text:
            subtitle_text = text

    if not title_text and filename_fallback:
        title_text = filename_fallback

    mapping: dict[str, str] = {}
    title_slots = [s for s in slots if s.role == "title"]
    subtitle_slots = [s for s in slots if s.role == "subtitle"]

    if title_slots and title_text:
        mapping[title_slots[0].object_id] = title_text

    if subtitle_slots and subtitle_text:
        mapping[subtitle_slots[0].object_id] = subtitle_text
    elif subtitle_slots and title_text and not subtitle_text:
        pass

    return mapping


def map_content_to_slots(
    classified: list[ClassifiedBlock],
    slots: list[TemplateSlot],
) -> dict[str, str]:
    title_text = ""
    subtitle_text = ""
    body_parts: list[str] = []

    for cb in classified:
        text = cb.block.text.strip()
        if not text:
            continue
        if cb.role == BlockRole.SLIDE_TITLE and not title_text:
            title_text = text
        elif cb.role == BlockRole.SLIDE_SUBTITLE and not subtitle_text:
            subtitle_text = text
        elif cb.role == BlockRole.BODY:
            body_parts.append(text)

    content_by_role = {
        "title": title_text,
        "subtitle": subtitle_text,
        "body": "\n".join(body_parts),
    }

    mapping: dict[str, str] = {}
    for slot in slots:
        text = content_by_role.get(slot.role, "")
        if text:
            mapping[slot.object_id] = text

    return mapping


def build_replace_requests(
    mapping: dict[str, str],
    presentation_id_hint: str = "",
) -> list[dict]:
    requests: list[dict] = []
    for object_id, new_text in mapping.items():
        requests.append({
            "deleteText": {
                "objectId": object_id,
                "textRange": {"type": "ALL"},
            }
        })
        requests.append({
            "insertText": {
                "objectId": object_id,
                "insertionIndex": 0,
                "text": new_text,
            }
        })
    return requests
