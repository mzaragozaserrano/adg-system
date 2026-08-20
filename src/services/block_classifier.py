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


_TITLE_SIZE_RATIO = 0.72
_SUBTITLE_MAX_SIZE_RATIO = 0.62
_COLOR_DISTANCE_THRESHOLD = 50.0


def _color_distance(
    c1: tuple[int, int, int] | None,
    c2: tuple[int, int, int] | None,
) -> float:
    if c1 is None or c2 is None:
        return 0.0
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def _colors_similar(
    c1: tuple[int, int, int] | None,
    c2: tuple[int, int, int] | None,
) -> bool:
    if c1 is None or c2 is None:
        return True
    return _color_distance(c1, c2) < _COLOR_DISTANCE_THRESHOLD


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
    colors = [b.color for b in blocks if b.color]
    if colors:
        merged.color = (
            sum(c[0] for c in colors) // len(colors),
            sum(c[1] for c in colors) // len(colors),
            sum(c[2] for c in colors) // len(colors),
        )
    return merged


def _group_title_lines(
    sorted_blocks: list[OcrBlock],
    max_h: float,
) -> tuple[list[OcrBlock], tuple[int, int, int] | None]:
    title_lines: list[OcrBlock] = []
    title_color: tuple[int, int, int] | None = None

    for block in sorted_blocks:
        rel_h = block.height / max(max_h, 1)
        if rel_h < _TITLE_SIZE_RATIO:
            break

        if not title_lines:
            title_lines.append(block)
            title_color = block.color
            continue

        prev = title_lines[-1]
        gap = block.y0 - prev.y1
        same_band = rel_h >= _TITLE_SIZE_RATIO
        same_color = _colors_similar(block.color, title_color)
        close = gap < prev.height * 2.0
        if same_band and same_color and close:
            title_lines.append(block)
        else:
            break

    return title_lines, title_color


def _find_subtitle_block(
    sorted_blocks: list[OcrBlock],
    title_lines: list[OcrBlock],
    max_h: float,
    title_color: tuple[int, int, int] | None,
) -> OcrBlock | None:
    if not title_lines:
        return None

    title_bottom = max(b.y1 for b in title_lines)
    title_h = max(b.height for b in title_lines)
    title_ids = {id(b) for b in title_lines}

    for block in sorted_blocks:
        if id(block) in title_ids:
            continue
        if block.y0 < title_bottom - block.height * 0.3:
            continue

        rel_to_title = block.height / max(title_h, 1)
        clearly_smaller = rel_to_title <= 0.85

        if title_color is None and block.color is None:
            if clearly_smaller:
                return block
            continue

        rel_h = block.height / max(max_h, 1)
        smaller = block.height < title_h * _SUBTITLE_MAX_SIZE_RATIO
        different_color = not _colors_similar(block.color, title_color)
        subtitle_band = rel_h < _TITLE_SIZE_RATIO

        if subtitle_band and (smaller or different_color):
            return block

    return None


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

    title_lines, title_color = _group_title_lines(sorted_blocks, max_h)
    subtitle_block = _find_subtitle_block(sorted_blocks, title_lines, max_h, title_color)

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

    assigned_ids = {id(b) for b in title_lines}
    if subtitle_block:
        assigned_ids.add(id(subtitle_block))

    for block in sorted_blocks:
        if id(block) not in assigned_ids:
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
