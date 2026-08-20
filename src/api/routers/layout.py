from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from google.oauth2.credentials import Credentials

from src.api.deps import get_google_credentials
from src.api.schemas import LayoutBuildResponse
from src.services.layout_builder import build_layout
from src.validators.slides_validator import extract_presentation_id

router = APIRouter(prefix="/layout", tags=["layout"])
logger = logging.getLogger(__name__)


@router.post("/build", response_model=LayoutBuildResponse)
def layout_build(
    url_or_id: str = Form(...),
    source_type: str = Form("slides"),
    filename: str = Form("Presentacion"),
    title_override: str = Form(""),
    subtitle_override: str = Form(""),
    pdf_file: UploadFile | None = File(default=None),
    creds: Credentials = Depends(get_google_credentials),
):
    if source_type not in ("slides", "pdf"):
        raise HTTPException(status_code=400, detail="source_type debe ser 'slides' o 'pdf'")

    pdf_bytes_direct: bytes | None = None
    source_id = url_or_id.strip()

    if pdf_file is not None:
        pdf_bytes_direct = pdf_file.file.read()
        if not filename or filename == "Presentacion":
            filename = pdf_file.filename or "Presentacion"
        source_type = "pdf"
        source_id = "local"
    else:
        try:
            source_id = extract_presentation_id(source_id)
        except Exception:
            pass

    logger.info(
        "layout_build start: source_type=%s filename=%s pdf_bytes=%s title=%r subtitle=%r",
        source_type,
        filename,
        len(pdf_bytes_direct) if pdf_bytes_direct else 0,
        title_override,
        subtitle_override,
    )

    try:
        result = build_layout(
            source_id=source_id,
            source_type=source_type,
            filename=filename,
            credentials=creds,
            title_override=title_override,
            subtitle_override=subtitle_override,
            pdf_bytes_direct=pdf_bytes_direct,
        )
    except ValueError as exc:
        logger.warning("layout_build ValueError: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("layout_build failed:\n%s", tb)
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "layout_build ok: id=%s slides=%d title=%r subtitle=%r",
        result.presentation_id,
        result.slides_processed,
        result.cover_title,
        result.cover_subtitle,
    )

    return LayoutBuildResponse(
        presentation_url=result.presentation_url,
        presentation_id=result.presentation_id,
        slides_processed=result.slides_processed,
        skipped_slides=result.skipped_slides,
        cover_title=result.cover_title,
        cover_subtitle=result.cover_subtitle,
    )
