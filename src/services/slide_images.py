from __future__ import annotations

import io
from pathlib import Path

import fitz
import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload

from src.integrations.google.clients import build_drive_client, build_slides_client


def _thumbnail_url_for_slide(
    slides_service,
    presentation_id: str,
    page_object_id: str,
) -> str | None:
    try:
        result = (
            slides_service.presentations()
            .pages()
            .getThumbnail(
                presentationId=presentation_id,
                pageObjectId=page_object_id,
                params_thumbnailPropertiesMimeType="PNG",
                params_thumbnailPropertiesThumbnailSize="LARGE",
            )
            .execute()
        )
        return result.get("contentUrl")
    except Exception:
        return None


def slides_to_page_images(
    presentation_id: str,
    credentials: Credentials,
) -> list[bytes]:
    slides_service = build_slides_client(credentials)
    presentation = slides_service.presentations().get(
        presentationId=presentation_id
    ).execute()

    images: list[bytes] = []
    for slide in presentation.get("slides", []):
        page_id = slide.get("objectId")
        url = _thumbnail_url_for_slide(slides_service, presentation_id, page_id)
        if not url:
            images.append(b"")
            continue
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=30.0)
            resp.raise_for_status()
            images.append(resp.content)
        except Exception:
            images.append(b"")

    return images


def pdf_to_page_images(pdf_path: Path, dpi: int = 150) -> list[bytes]:
    doc = fitz.open(str(pdf_path))
    images: list[bytes] = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def pdf_bytes_to_page_images(pdf_bytes: bytes, dpi: int = 150) -> list[bytes]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: list[bytes] = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def download_drive_pdf(file_id: str, credentials: Credentials) -> bytes:
    drive = build_drive_client(credentials)
    request = drive.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()
