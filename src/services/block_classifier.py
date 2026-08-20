from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from src.services.ocr_blocks import OcrBlock, OcrWord

_SECTION_NUMBER_RE = re.compile(r"^\d{1,2}\.$")

_OCR_BRAND_NOISE_COMPACT = (
    "notebooklm",
    "adgravity",
)
_OCR_BRAND_NOISE_SUBSTRINGS = (
    "ad gravity",
    "notebook lm",
)

_SUBTITLE_MAX_HEIGHT_RATIO = 0.78


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


def _normalize_noise_text(text: str) -> str:
    return re.sub(r"[\s\-_]+", "", text.lower())


def is_ocr_brand_noise(block: OcrBlock) -> bool:
    text = block.text.strip().lower()
    if not text:
        return False
    compact = _normalize_noise_text(text)
    if any(token in compact for token in _OCR_BRAND_NOISE_COMPACT):
        return True
    return any(token in text for token in _OCR_BRAND_NOISE_SUBSTRINGS)


def filter_ocr_brand_noise(blocks: list[OcrBlock]) -> list[OcrBlock]:
    return [b for b in blocks if not is_ocr_brand_noise(b)]


def _is_cover_noise(block: OcrBlock, img_width: float, img_height: float) -> bool:
    if is_ocr_brand_noise(block):
        return True
    if block.y1 > img_height * 0.93 and block.height < img_height * 0.06:
        return True
    if block.y0 < img_height * 0.08 and block.x0 > img_width * 0.55 and block.height < img_height * 0.06:
        return True
    return False


def _line_ordered_words(words: list[OcrWord]) -> list[OcrWord]:
    """Agrupa palabras por línea visual y ordena por x0 dentro de cada línea.
    Evita el reordenamiento incorrecto causado por variaciones de y0 en la misma línea."""
    if not words:
        return []

    words_sorted = sorted(words, key=lambda w: w.y0)
    lines: list[list[OcrWord]] = []

    for word in words_sorted:
        word_mid = (word.y0 + word.y1) / 2
        placed = False
        for line in lines:
            line_y0 = min(w.y0 for w in line)
            line_y1 = max(w.y1 for w in line)
            if line_y0 <= word_mid <= line_y1:
                line.append(word)
                placed = True
                break
        if not placed:
            lines.append([word])

    for line in lines:
        line.sort(key=lambda w: w.x0)

    lines.sort(key=lambda line: min(w.y0 for w in line))

    return [w for line in lines for w in line]


def _join_block_texts(blocks: list[OcrBlock]) -> OcrBlock:
    """Crea un OcrBlock cuyo texto es la unión de los textos de los bloques
    en orden vertical, con palabras ordenadas por línea dentro de cada bloque."""
    blocks_sorted = sorted(blocks, key=lambda b: b.y0)
    merged = OcrBlock()
    for block in blocks_sorted:
        merged.words.extend(_line_ordered_words(block.words))
    return merged


def _group_title_blocks(sorted_blocks: list[OcrBlock]) -> list[OcrBlock]:
    """Bloque(s) de título: el primero que sea suficientemente grande y los
    bloques consecutivos de tamaño similar (>= 80% del primero)."""
    if not sorted_blocks:
        return []

    title_blocks: list[OcrBlock] = []
    for block in sorted_blocks:
        if not title_blocks:
            max_h = max(b.height for b in sorted_blocks)
            if block.height >= max_h * 0.55:
                title_blocks.append(block)
            continue

        prev = title_blocks[-1]
        gap = block.y0 - prev.y1
        similar_size = block.height >= title_blocks[0].height * 0.80
        close_vertically = gap < prev.height * 2.5

        if similar_size and close_vertically:
            title_blocks.append(block)
        else:
            break

    return title_blocks


def _find_and_group_subtitle_blocks(
    sorted_blocks: list[OcrBlock],
    title_blocks: list[OcrBlock],
) -> list[OcrBlock]:
    """Primer bloque debajo del título claramente más pequeño, más los
    bloques consecutivos de tamaño similar que formen parte del mismo subtítulo."""
    if not title_blocks:
        return []

    title_bottom = max(b.y1 for b in title_blocks)
    min_title_h = min(b.height for b in title_blocks)
    title_ids = {id(b) for b in title_blocks}

    subtitle_blocks: list[OcrBlock] = []
    for block in sorted_blocks:
        if id(block) in title_ids:
            continue
        if block.y0 < title_bottom - block.height * 0.5:
            continue

        if not subtitle_blocks:
            if block.height < min_title_h * _SUBTITLE_MAX_HEIGHT_RATIO:
                subtitle_blocks.append(block)
            continue

        prev = subtitle_blocks[-1]
        gap = block.y0 - prev.y1
        similar_size = block.height >= subtitle_blocks[0].height * 0.75
        close = gap < prev.height * 2.5
        if similar_size and close:
            subtitle_blocks.append(block)
        else:
            break

    return subtitle_blocks


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

    title_blocks = _group_title_blocks(sorted_blocks)
    subtitle_blocks = _find_and_group_subtitle_blocks(sorted_blocks, title_blocks)

    result: list[ClassifiedBlock] = []
    if title_blocks:
        merged = _join_block_texts(title_blocks)
        result.append(ClassifiedBlock(
            block=merged,
            role=BlockRole.COVER_TITLE,
            confidence=0.9,
        ))

    if subtitle_blocks:
        merged_sub = _join_block_texts(subtitle_blocks)
        result.append(ClassifiedBlock(
            block=merged_sub,
            role=BlockRole.COVER_SUBTITLE,
            confidence=0.85,
        ))

    assigned_ids = {id(b) for b in title_blocks}
    for sb in subtitle_blocks:
        assigned_ids.add(id(sb))

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

    blocks = filter_ocr_brand_noise(blocks)
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
    blocks = filter_ocr_brand_noise(blocks)
    if not blocks:
        return []

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
