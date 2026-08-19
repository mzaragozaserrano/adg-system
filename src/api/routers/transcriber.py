from fastapi import APIRouter, Depends, HTTPException
from google.oauth2.credentials import Credentials

from src.api.deps import get_google_credentials
from src.api.schemas import TranscribeRequest
from src.services.drive_files import assert_google_slides_file
from src.services.transcriber import transcribe_slides
from src.validators.slides_validator import extract_presentation_id

router = APIRouter(prefix="/transcriber", tags=["transcriber"])


@router.post("/transcribe")
def transcribe(
    body: TranscribeRequest,
    creds: Credentials = Depends(get_google_credentials),
):
    presentation_id = extract_presentation_id(body.url_or_id)
    assert_google_slides_file(creds, presentation_id)
    try:
        result = transcribe_slides(
            presentation_id=presentation_id,
            slide_numbers=body.slide_numbers,
            new_document=body.new_document,
            credentials=creds,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result
