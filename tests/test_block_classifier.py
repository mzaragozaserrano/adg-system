from src.services.block_classifier import BlockRole, classify_cover_slide
from src.services.ocr_blocks import OcrBlock, OcrWord


def _block(text: str, y0: float, height: float, x0: float = 80.0) -> OcrBlock:
    block = OcrBlock()
    block.words.append(
        OcrWord(text=text, x0=x0, y0=y0, x1=x0 + 400, y1=y0 + height)
    )
    return block


def test_classify_cover_merges_title_lines_by_size():
    blocks = [
        _block("TOTAL REACH", y0=180, height=55),
        _block("BLACK FRIDAY 2026", y0=245, height=55),
        _block("Domina la atención cuando todos compiten por ella.", y0=320, height=30),
        _block("ad gravity", y0=20, height=12, x0=700),
        _block("NotebookLM", y0=500, height=10, x0=650),
    ]

    classified = classify_cover_slide(blocks, img_width=1024, img_height=576)

    roles = {cb.role: cb.block.text for cb in classified}
    assert roles[BlockRole.COVER_TITLE] == "TOTAL REACH BLACK FRIDAY 2026"
    assert roles[BlockRole.COVER_SUBTITLE] == "Domina la atención cuando todos compiten por ella."


def test_classify_cover_detects_subtitle_by_smaller_size():
    blocks = [
        _block("Mi propuesta comercial", y0=200, height=50),
        _block("Una solución integral para el cliente.", y0=270, height=28),
    ]

    classified = classify_cover_slide(blocks, img_width=1024, img_height=576)

    roles = {cb.role: cb.block.text for cb in classified}
    assert roles[BlockRole.COVER_TITLE] == "Mi propuesta comercial"
    assert roles[BlockRole.COVER_SUBTITLE] == "Una solución integral para el cliente."


def test_classify_cover_without_subtitle():
    blocks = [
        _block("Solo título grande", y0=200, height=55),
    ]

    classified = classify_cover_slide(blocks, img_width=1024, img_height=576)

    roles = {cb.role for cb in classified}
    assert BlockRole.COVER_TITLE in roles
    assert BlockRole.COVER_SUBTITLE not in roles


def test_classify_cover_no_subtitle_when_similar_size():
    blocks = [
        _block("TITULO PRINCIPAL", y0=200, height=55),
        _block("Otra línea del mismo tamaño", y0=265, height=52),
    ]

    classified = classify_cover_slide(blocks, img_width=1024, img_height=576)

    roles = {cb.role: cb.block.text for cb in classified}
    assert "TITULO PRINCIPAL" in roles.get(BlockRole.COVER_TITLE, "")
    assert BlockRole.COVER_SUBTITLE not in roles
