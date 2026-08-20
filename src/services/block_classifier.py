from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from src.services.ocr_blocks import OcrBlock

_SECTION_NUMBER_RE = re.compile(r"^\d{1,2}\.$")


class BlockRole(str, Enum):
    COVER_TITLE = "cover_title"
    COVER_SUBTITLE = "cover_subtitle"
    SECTION_NUMBER = "section_number"
    SECTION_TITLE = "section_title"
    SLIDE_TITLE = "slide_title"
    SLIDE_SUBTITLE = "slide_subtitle"
    BODY = "body"


@dataclass
class ClassifiedBlock:
    block: OcrBlock
    role: BlockRole
    confidence: float


def _relative_height(block: OcrBlock, img_height: float) -> float:
    if img_height <= 0:
        return 0.0
    return block.height / img_height


def _is_top_zone(block: OcrBlock, img_height: float, ratio: float = 0.30) -> bool:
    return block.y0 < img_height * ratio


def _is_left_zone(block: OcrBlock, img_width: float, ratio: float = 0.55) -> bool:
    return block.x0 < img_width * ratio


def _is_centered(block: OcrBlock, img_width: float, margin: float = 0.15) -> bool:
    center = img_width / 2
    return abs(block.cx - center) < img_width * margin


def _is_section_number(block: OcrBlock) -> bool:
    return bool(_SECTION_NUMBER_RE.match(block.text.strip()))


def _word_count(block: OcrBlock) -> int:
    return len(block.text.split())


def _char_count(block: OcrBlock) -> int:
    return len(block.text.strip())


def classify_cover_slide(
    blocks: list[OcrBlock],
    img_width: float,
    img_height: float,
) -> list[ClassifiedBlock]:
    if not blocks:
        return []

    sorted_by_height = sorted(blocks, key=lambda b: b.height, reverse=True)
    max_h = sorted_by_height[0].height if sorted_by_height else 1.0

    scored: list[tuple[float, OcrBlock]] = []
    for block in blocks:
        score = (block.height / max(max_h, 1)) * 0.6
        if _is_centered(block, img_width):
            score += 0.2
        if _word_count(block) <= 10:
            score += 0.1
        if block.y0 < img_height * 0.6:
            score += 0.1
        scored.append((score, block))

    scored.sort(key=lambda x: (-x[0], x[1].y0))
    result: list[ClassifiedBlock] = []
    assigned_title = False

    for score, block in scored:
        text = block.text.strip()
        if not text:
            continue

        if not assigned_title and score >= 0.5:
            result.append(ClassifiedBlock(block=block, role=BlockRole.COVER_TITLE, confidence=score))
            assigned_title = True
        elif assigned_title and len(result) == 1 and score >= 0.3:
            result.append(ClassifiedBlock(block=block, role=BlockRole.COVER_SUBTITLE, confidence=score))
        else:
            result.append(ClassifiedBlock(block=block, role=BlockRole.BODY, confidence=score))

    return result


def classify_content_slide(
    blocks: list[OcrBlock],
    img_width: float,
    img_height: float,
) -> list[ClassifiedBlock]:
    if not blocks:
        return []

    if _detect_section_slide(blocks, img_width, img_height):
        return _classify_section_slide(blocks, img_width, img_height)

    max_h = max((b.height for b in blocks), default=1.0)
    result: list[ClassifiedBlock] = []
    assigned_title = False
    assigned_subtitle = False

    blocks_sorted = sorted(blocks, key=lambda b: b.y0)

    for block in blocks_sorted:
        text = block.text.strip()
        if not text:
            continue

        rel_h = block.height / max(max_h, 1)
        in_top = _is_top_zone(block, img_height)
        in_left = _is_left_zone(block, img_width)

        if not assigned_title and in_top and in_left and rel_h >= 0.35:
            result.append(ClassifiedBlock(
                block=block,
                role=BlockRole.SLIDE_TITLE,
                confidence=0.7 + rel_h * 0.2,
            ))
            assigned_title = True

        elif (
            not assigned_subtitle
            and assigned_title
            and in_top
            and in_left
            and rel_h >= 0.20
            and _word_count(block) <= 15
        ):
            result.append(ClassifiedBlock(
                block=block,
                role=BlockRole.SLIDE_SUBTITLE,
                confidence=0.5 + rel_h * 0.2,
            ))
            assigned_subtitle = True

        else:
            result.append(ClassifiedBlock(
                block=block,
                role=BlockRole.BODY,
                confidence=0.8,
            ))

    return result


def _detect_section_slide(
    blocks: list[OcrBlock],
    img_width: float,
    img_height: float,
) -> bool:
    max_h = max((b.height for b in blocks), default=1.0)
    for block in blocks:
        if not _is_section_number(block):
            continue
        rel_h = block.height / max(max_h, 1)
        if rel_h >= 0.5 and _is_centered(block, img_width, margin=0.25):
            return True
    return False


def _classify_section_slide(
    blocks: list[OcrBlock],
    img_width: float,
    img_height: float,
) -> list[ClassifiedBlock]:
    max_h = max((b.height for b in blocks), default=1.0)
    result: list[ClassifiedBlock] = []
    section_num_assigned = False
    section_title_assigned = False

    for block in sorted(blocks, key=lambda b: b.y0):
        text = block.text.strip()
        if not text:
            continue

        rel_h = block.height / max(max_h, 1)

        if not section_num_assigned and _is_section_number(block) and rel_h >= 0.5:
            result.append(ClassifiedBlock(
                block=block,
                role=BlockRole.SECTION_NUMBER,
                confidence=0.95,
            ))
            section_num_assigned = True

        elif section_num_assigned and not section_title_assigned and rel_h >= 0.20:
            result.append(ClassifiedBlock(
                block=block,
                role=BlockRole.SECTION_TITLE,
                confidence=0.80,
            ))
            section_title_assigned = True

        else:
            result.append(ClassifiedBlock(
                block=block,
                role=BlockRole.BODY,
                confidence=0.7,
            ))

    return result


def infer_cover_title_from_filename(filename: str) -> str:
    name = filename
    for ext in (".pdf", ".pptx", ".ppt"):
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()
