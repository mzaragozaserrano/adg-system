from datetime import datetime
from pathlib import Path

from config.settings import settings
from src.dla.extractor import PDFExtractor
from src.llm.mapper import GeminiMapper
from src.slides.renderer import SlidesRenderer


class MaquetadorPipeline:
    def __init__(self) -> None:
        self._extractor = PDFExtractor()
        self._mapper = GeminiMapper()
        self._renderer = SlidesRenderer()

    def run(self, pdf_path: Path, presentation_name: str | None = None) -> dict:
        extracted_text = self._extractor.extract_tables_markdown(pdf_path)
        mapped_data = self._mapper.map_to_template(extracted_text)

        if not presentation_name:
            titulo = mapped_data.get("titulo_slide", "Presentacion ADG")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            presentation_name = f"{titulo}_{timestamp}"

        url = self._renderer.render(presentation_name, mapped_data)

        return {
            "url": url,
            "mapped_data": mapped_data,
            "extracted_text": extracted_text,
        }
