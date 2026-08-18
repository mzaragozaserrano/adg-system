from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_current_user
from src.api.schemas import TranscribeRequest
from src.auth.security import credentials_from_encrypted
from src.db.models import User
from src.services.drive_files import assert_google_slides_file
from src.services.transcriber import transcribe_slides
from src.validators.slides_validator import extract_presentation_id

router = APIRouter(prefix="/transcriber", tags=["transcriber"])


@router.post("/transcribe")
def transcribe(
    body: TranscribeRequest,
    user: User = Depends(get_current_user),
):
    if not user.google_token_encrypted:
        raise HTTPException(status_code=400, detail="Cuenta Google no vinculada")

    creds = credentials_from_encrypted(user.google_token_encrypted)
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
