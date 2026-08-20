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


def _is_mostly_uppercase(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) >= 0.7


def _looks_like_subtitle(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith((".", "?", "!")):
        return True
    if not _is_mostly_uppercase(stripped) and _word_count_text(stripped) >= 4:
        return True
    return False


def _word_count_text(text: str) -> int:
    return len(text.split())


def _is_cover_noise(block: OcrBlock, img_width: float, img_height: float) -> bool:
    text = block.text.strip().lower()
    if any(token in text for token in ("notebooklm", "ad gravity", "adgravity", "adg media")):
        return True
    if block.y1 > img_height * 0.88:
        return True
    if block.y0 < img_height * 0.08 and block.x0 > img_width * 0.55:
        return True
    if block.height < img_height * 0.035 and len(text) < 20:
        return True
    return False


def _merge_blocks(blocks: list[OcrBlock]) -> OcrBlock:
    merged = OcrBlock()
    for block in blocks:
        merged.words.extend(block.words)
    merged.words.sort(key=lambda w: (w.y0, w.x0))
    return merged


def classify_cover_slide(
    blocks: list[OcrBlock],
    img_width: float,
    img_height: float,
) -> list[ClassifiedBlock]:
    if not blocks:
        return []

    main_blocks = [
        b for b in blocks
        if b.text.strip() and not _is_cover_noise(b, img_width, img_height)
    ]
    if not main_blocks:
        main_blocks = [b for b in blocks if b.text.strip()]

    sorted_blocks = sorted(main_blocks, key=lambda b: b.y0)
    max_h = max(b.height for b in sorted_blocks)

    title_lines: list[OcrBlock] = []
    subtitle_block: OcrBlock | None = None

    for block in sorted_blocks:
        text = block.text.strip()
        rel_h = block.height / max(max_h, 1)

        if _looks_like_subtitle(text) and title_lines:
            subtitle_block = block
            break

        if rel_h >= 0.55 or (_is_mostly_uppercase(text) and rel_h >= 0.35):
            title_lines.append(block)
        elif not title_lines and rel_h >= 0.35:
            title_lines.append(block)
        elif title_lines and not subtitle_block and rel_h >= 0.25:
            subtitle_block = block
            break

    if not subtitle_block and title_lines:
        remaining = [b for b in sorted_blocks if b not in title_lines]
        for block in remaining:
            if _looks_like_subtitle(block.text):
                subtitle_block = block
                break

    result: list[ClassifiedBlock] = []
    if title_lines:
        merged = _merge_blocks(title_lines)
        result.append(ClassifiedBlock(
            block=merged,
            role=BlockRole.COVER_TITLE,
            confidence=0.9,
        ))

    if subtitle_block:
        result.append(ClassifiedBlock(
            block=subtitle_block,
            role=BlockRole.COVER_SUBTITLE,
            confidence=0.85,
        ))

    assigned = {id(cb.block) for cb in result}
    for block in sorted_blocks:
        if id(block) not in assigned and block is not subtitle_block and block not in title_lines:
            result.append(ClassifiedBlock(block=block, role=BlockRole.BODY, confidence=0.5))

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
