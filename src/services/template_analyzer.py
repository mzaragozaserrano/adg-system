from __future__ import annotations

from dataclasses import dataclass

from src.validators.slides_text import collect_slides_text_spans, dimension_to_points


_FIXED_TEXTS = {
    "adg",
    "adgravity",
    "adg media group",
    "media group",
    "www.",
    "http",
    "@",
    "confidencial",
    "copyright",
    "©",
}

_SLIDE_W_PT = 720.0
_SLIDE_H_PT = 405.0


@dataclass
class TemplateSlot:
    object_id: str
    role: str
    sample_text: str
    font_size: float
    bold: bool
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def area(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


def _looks_fixed(text: str) -> bool:
    lower = text.lower().strip()
    if any(token in lower for token in _FIXED_TEXTS):
        return True
    if len(lower) <= 2:
        return True
    return False


def _element_bbox_from_slide(slide: dict, object_id: str) -> tuple[float, float, float, float] | None:
    for el in slide.get("pageElements", []):
        if el.get("objectId") == object_id:
            transform = el.get("transform", {})
            size = el.get("size", {})
            tx = dimension_to_points({"magnitude": transform.get("translateX", 0), "unit": "EMU"})
            ty = dimension_to_points({"magnitude": transform.get("translateY", 0), "unit": "EMU"})
            sx = transform.get("scaleX") or 1
            sy = transform.get("scaleY") or 1
            w = dimension_to_points(size.get("width")) * abs(sx)
            h = dimension_to_points(size.get("height")) * abs(sy)
            return (tx, ty, tx + w, ty + h)
    return None


def analyze_template_slide(slide: dict, theme_fonts: dict | None) -> list[TemplateSlot]:
    spans = collect_slides_text_spans(slide, theme_fonts)

    seen_objects: dict[str, dict] = {}
    for bbox, text, data in spans:
        oid = data["object_id"]
        if oid not in seen_objects:
            seen_objects[oid] = {
                "texts": [],
                "font_size": data.get("size", 0.0),
                "bold": data.get("bold", False),
                "bbox": bbox,
            }
        seen_objects[oid]["texts"].append(text)

    candidates: list[TemplateSlot] = []
    for oid, info in seen_objects.items():
        full_text = " ".join(info["texts"]).strip()
        if not full_text:
            continue
        if _looks_fixed(full_text):
            continue

        bbox = info["bbox"]
        slot = TemplateSlot(
            object_id=oid,
            role="",
            sample_text=full_text,
            font_size=info["font_size"],
            bold=info["bold"],
            x0=bbox[0],
            y0=bbox[1],
            x1=bbox[2],
            y1=bbox[3],
        )
        candidates.append(slot)

    candidates.sort(key=lambda s: (s.font_size, s.area), reverse=True)
    for i, slot in enumerate(candidates):
        if i == 0:
            slot.role = "title"
        elif i == 1:
            slot.role = "subtitle"
        else:
            slot.role = "body"

    return candidates
