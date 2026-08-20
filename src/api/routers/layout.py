from fastapi import APIRouter, Depends, HTTPException
from google.oauth2.credentials import Credentials

from src.api.deps import get_google_credentials
from src.api.schemas import LayoutBuildRequest, LayoutBuildResponse
from src.services.layout_builder import build_layout
from src.validators.slides_validator import extract_presentation_id

router = APIRouter(prefix="/layout", tags=["layout"])


@router.post("/build", response_model=LayoutBuildResponse)
def layout_build(
    body: LayoutBuildRequest,
    creds: Credentials = Depends(get_google_credentials),
):
    source_id = extract_presentation_id(body.url_or_id)
    try:
        result = build_layout(
            source_id=source_id,
            source_type=body.source_type,
            filename=body.filename,
            credentials=creds,
            title_override=body.title_override,
            subtitle_override=body.subtitle_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LayoutBuildResponse(
        presentation_url=result.presentation_url,
        presentation_id=result.presentation_id,
        slides_processed=result.slides_processed,
        skipped_slides=result.skipped_slides,
        cover_title=result.cover_title,
        cover_subtitle=result.cover_subtitle,
    )
