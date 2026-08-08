from pathlib import Path

from docling.document_converter import DocumentConverter


class PDFExtractor:
    def __init__(self) -> None:
        self._converter = DocumentConverter()

    def extract(self, pdf_path: Path) -> str:
        result = self._converter.convert(str(pdf_path))
        markdown = result.document.export_to_markdown()
        return markdown

    def extract_tables_markdown(self, pdf_path: Path) -> str:
        result = self._converter.convert(str(pdf_path))
        tables: list[str] = []
        for table in result.document.tables:
            tables.append(table.export_to_markdown())
        return "\n\n".join(tables) if tables else result.document.export_to_markdown()
