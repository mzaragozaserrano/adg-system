import fitz


def describe_position(bbox: tuple, page_width: float, page_height: float) -> str:
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2

    h = (
        "izquierda"
        if cx < page_width * 0.33
        else "centro" if cx < page_width * 0.66 else "derecha"
    )
    v = (
        "superior"
        if cy < page_height * 0.33
        else "centro" if cy < page_height * 0.66 else "inferior"
    )
    return f"{v} {h}"


def format_location(bbox: tuple, page_width: float, page_height: float) -> str:
    zone = describe_position(bbox, page_width, page_height)
    x0, y0, x1, y1 = bbox
    return f"{zone} (x: {int(x0)}–{int(x1)}, y: {int(y0)}–{int(y1)})"


def find_related_text(
    rect: fitz.Rect,
    text_spans: list[tuple[tuple, str]],
    page_height: float,
) -> str:
    inside: list[str] = []
    nearby: list[tuple[float, str]] = []

    rcx = (rect.x0 + rect.x1) / 2
    rcy = (rect.y0 + rect.y1) / 2

    for bbox, text in text_spans:
        if not text.strip():
            continue
        text_rect = fitz.Rect(bbox)
        if rect.intersects(text_rect) or rect.contains(text_rect):
            inside.append(text.strip())
            continue
        tcx = (text_rect.x0 + text_rect.x1) / 2
        tcy = (text_rect.y0 + text_rect.y1) / 2
        dist = ((rcx - tcx) ** 2 + (rcy - tcy) ** 2) ** 0.5
        nearby.append((dist, text.strip()))

    if inside:
        unique = list(dict.fromkeys(inside))
        return " · ".join(unique[:3])

    if nearby:
        nearby.sort(key=lambda x: x[0])
        threshold = page_height * 0.08
        close = [t for d, t in nearby if d <= threshold]
        if close:
            return " · ".join(list(dict.fromkeys(close))[:3])

    return ""


def describe_graphic_element(draw: dict, related_text: str, label: str) -> str:
    kind = "Relleno" if label == "relleno" else "Trazo / borde"
    if related_text:
        return f"{kind} (asociado a «{related_text}»)"
    return f"{kind} de elemento gráfico"
