from src.services.block_classifier import (
    BlockRole,
    _line_ordered_words,
    classify_content_slide,
    classify_cover_slide,
    filter_ocr_brand_noise,
    is_ocr_brand_noise,
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


def test_classify_cover_splits_merged_ocr_block_by_line_height():
    """Vision API a veces devuelve título y subtítulo en un único bloque."""
    block = OcrBlock()
    block.words.extend([
        _word("TOTAL", 80, 280, 220, 335),
        _word("REACH", 230, 282, 400, 336),
        _word("BLACK", 80, 345, 220, 400),
        _word("FRIDAY", 230, 347, 400, 401),
        _word("2026", 410, 346, 500, 400),
        _word("Domina", 80, 420, 180, 448),
        _word("la", 185, 421, 210, 447),
        _word("atención", 215, 420, 340, 449),
        _word("cuando", 345, 422, 450, 448),
        _word("todos", 80, 455, 160, 482),
        _word("compiten", 165, 456, 280, 483),
        _word("por", 285, 455, 330, 481),
        _word("ella.", 335, 456, 410, 482),
    ])

    classified = classify_cover_slide([block], img_width=1024, img_height=576)
    roles = {cb.role: cb.block.text for cb in classified}

    assert "TOTAL REACH" in roles[BlockRole.COVER_TITLE]
    assert "BLACK FRIDAY 2026" in roles[BlockRole.COVER_TITLE]
    assert "Domina" not in roles[BlockRole.COVER_TITLE]
    assert "Domina" in roles[BlockRole.COVER_SUBTITLE]
    assert "compiten por ella" in roles[BlockRole.COVER_SUBTITLE]


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


def test_is_ocr_brand_noise_detects_variants():
    assert is_ocr_brand_noise(_block("NotebookLM", y0=530, height=10))
    assert is_ocr_brand_noise(_block("notebook lm", y0=530, height=10))
    assert is_ocr_brand_noise(_block("ad gravity", y0=20, height=12, x0=700))
    assert is_ocr_brand_noise(_block("ADGRAVITY", y0=20, height=12, x0=700))
    assert not is_ocr_brand_noise(_block("TOTAL REACH", y0=280, height=55))


def test_filter_ocr_brand_noise_removes_brand_blocks():
    blocks = [
        _block("TOTAL REACH", y0=280, height=55),
        _block("ad gravity", y0=20, height=12, x0=700),
        _block("NotebookLM", y0=530, height=10, x0=650),
    ]
    filtered = filter_ocr_brand_noise(blocks)
    assert len(filtered) == 1
    assert filtered[0].text == "TOTAL REACH"


def test_classify_content_slide_omits_brand_noise():
    blocks = [
        _block("Estrategia de campaña", y0=40, height=40),
        _block("adgravity", y0=10, height=12, x0=700),
        _block("NotebookLM", y0=550, height=10, x0=650),
        _block("Contenido del cuerpo de la diapositiva.", y0=120, height=20),
    ]

    classified = classify_content_slide(blocks, img_width=1024, img_height=576)
    texts = [cb.block.text for cb in classified]

    assert "adgravity" not in " ".join(texts).lower()
    assert "notebooklm" not in " ".join(texts).lower()
    assert any("Estrategia" in t for t in texts)
    assert any("Contenido" in t for t in texts)
