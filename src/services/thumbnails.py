import time
from pathlib import Path

import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import settings
from src.services.presentation_cache import get_cached_presentation

CACHE_TTL_SECONDS = 60 * 60


def get_slide_thumbnail(
    credentials: Credentials,
    presentation_id: str,
    slide_number: int,
    width: int = 400,
) -> Path:
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    image_path = settings.exports_dir / f"{presentation_id}_slide_{slide_number}.png"
    if image_path.exists():
        age = time.time() - image_path.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            return image_path

    slides_service = build("slides", "v1", credentials=credentials)
    presentation = get_cached_presentation(slides_service, presentation_id)
    slides = presentation.get("slides", [])
    if slide_number < 1 or slide_number > len(slides):
        raise ValueError("Número de diapositiva fuera de rango")

    page_id = slides[slide_number - 1]["objectId"]
    thumbnail = (
        slides_service.presentations()
        .pages()
        .getThumbnail(presentationId=presentation_id, pageObjectId=page_id)
        .execute()
    )
    content_url = thumbnail.get("contentUrl")
    if not content_url:
        raise ValueError("No se pudo obtener miniatura de la diapositiva")

    response = httpx.get(content_url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    image_path.write_bytes(response.content)
    return image_path


def warm_slide_thumbnails(
    credentials: Credentials,
    presentation_id: str,
    slide_numbers: list[int],
) -> list[int]:
    warmed: list[int] = []
    for slide_number in sorted(set(slide_numbers)):
        try:
            get_slide_thumbnail(credentials, presentation_id, slide_number)
            warmed.append(slide_number)
        except (ValueError, httpx.HTTPError, OSError):
            continue
    return warmed
