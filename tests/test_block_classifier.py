from src.services.block_classifier import (
    BlockRole,
    _line_ordered_words,
    classify_cover_slide,
)
from src.services.ocr_blocks import OcrBlock, OcrWord


def _block(text: str, y0: float, height: float, x0: float = 80.0) -> OcrBlock:
    block = OcrBlock()
    block.words.append(
        OcrWord(text=text, x0=x0, y0=y0, x1=x0 + 400, y1=y0 + height)
    )
    return block


def _word(text: str, x0: float, y0: float, x1: float, y1: float) -> OcrWord:
    return OcrWord(text=text, x0=x0, y0=y0, x1=x1, y1=y1)


def test_classify_cover_merges_title_lines_by_size():
    blocks = [
        _block("TOTAL REACH", y0=280, height=55),
        _block("BLACK FRIDAY 2026", y0=345, height=55),
        _block("Domina la atención cuando todos compiten por ella.", y0=420, height=30),
        _block("ad gravity", y0=20, height=12, x0=700),
        _block("NotebookLM", y0=530, height=10, x0=650),
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


def test_classify_cover_title_not_filtered_in_lower_half():
    """El título no debe filtrarse aunque esté en la mitad inferior del slide."""
    blocks = [
        _block("TITULO GRANDE", y0=340, height=80),
        _block("Subtítulo descriptivo", y0=440, height=30),
    ]
    img_height = 520.0

    classified = classify_cover_slide(blocks, img_width=1024, img_height=img_height)

    roles = {cb.role: cb.block.text for cb in classified}
    assert roles[BlockRole.COVER_TITLE] == "TITULO GRANDE"
    assert roles[BlockRole.COVER_SUBTITLE] == "Subtítulo descriptivo"


def test_line_ordered_words_corrects_y_variation():
    """Palabras en la misma línea pero con y0 ligeramente distintas deben ordenarse por x0."""
    words = [
        _word("compiten", x0=80, y0=365, x1=180, y1=390),
        _word("por", x0=195, y0=360, x1=230, y1=385),
        _word("ella", x0=240, y0=358, x1=285, y1=382),
        _word(".", x0=290, y0=356, x1=300, y1=380),
    ]

    result = _line_ordered_words(words)
    assert [w.text for w in result] == ["compiten", "por", "ella", "."]
