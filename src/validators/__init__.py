from pathlib import Path

from google.oauth2.credentials import Credentials

from src.validators.models import ValidationResult
from src.validators.pdf_validator import PDFValidator
from src.validators.slides_validator import SlidesValidator, extract_presentation_id


def validate_pdf(pdf_path: Path) -> ValidationResult:
    return PDFValidator().validate(pdf_path)


def validate_slides(
    url_or_id: str,
    credentials: Credentials | None = None,
) -> ValidationResult:
    return SlidesValidator(credentials=credentials).validate(url_or_id)


__all__ = [
    "validate_pdf",
    "validate_slides",
    "extract_presentation_id",
    "ValidationResult",
]
