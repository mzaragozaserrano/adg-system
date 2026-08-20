from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field

import httpx
from google.cloud import vision


@dataclass
class OcrWord:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class OcrBlock:
    words: list[OcrWord] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def x0(self) -> float:
        return min(w.x0 for w in self.words) if self.words else 0.0

    @property
    def y0(self) -> float:
        return min(w.y0 for w in self.words) if self.words else 0.0

    @property
    def x1(self) -> float:
        return max(w.x1 for w in self.words) if self.words else 0.0

    @property
    def y1(self) -> float:
        return max(w.y1 for w in self.words) if self.words else 0.0

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


_vision_client: vision.ImageAnnotatorClient | None = None


def _get_vision_client() -> vision.ImageAnnotatorClient:
    global _vision_client
    if _vision_client is None:
        sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if sa_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, prefix="adg_sa_"
            )
            tmp.write(sa_json)
            tmp.flush()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client


def _vertices_to_bbox(vertices: list) -> tuple[float, float, float, float]:
    xs = [v.x for v in vertices if v.x]
    ys = [v.y for v in vertices if v.y]
    if not xs or not ys:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def ocr_image_bytes_structured(image_bytes: bytes) -> list[OcrBlock]:
    client = _get_vision_client()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if not response.full_text_annotation:
        return []

    blocks: list[OcrBlock] = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            if block.block_type != vision.Block.BlockType.TEXT:
                continue
            ocr_block = OcrBlock()
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    word_text = "".join(
                        symbol.text for symbol in word.symbols
                    )
                    if not word_text.strip():
                        continue
                    x0, y0, x1, y1 = _vertices_to_bbox(
                        word.bounding_box.vertices
                    )
                    ocr_block.words.append(
                        OcrWord(text=word_text, x0=x0, y0=y0, x1=x1, y1=y1)
                    )
            if ocr_block.words:
                blocks.append(ocr_block)

    return blocks


def ocr_url_structured(content_url: str) -> list[OcrBlock]:
    response = httpx.get(content_url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return ocr_image_bytes_structured(response.content)
