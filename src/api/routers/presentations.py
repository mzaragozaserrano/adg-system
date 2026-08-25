import json
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from src.api.deps import (
    assign_issue_ids,
    get_current_user,
    get_google_credentials,
    get_user_validation_record,
    save_validation_record,
)
from src.api.schemas import ExportRequest, FixRequest, SlidesValidateRequest
from src.db.models import FixRecord, User, ValidationRecord, get_db
from src.fixers.slides_fixer import SlidesFixer, issue_from_fix_input, parse_google_http_error
from src.services.drive_files import assert_google_slides_file
from src.services.report_pdf import generate_report_pdf
from src.services.thumbnails import get_slide_thumbnail, warm_slide_thumbnails
from src.validators import validate_pdf, validate_slides
from src.validators.slides_validator import extract_presentation_id

router = APIRouter(prefix="/presentations", tags=["presentations"])


@router.post("/validate/pdf")
async def validate_pdf_upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se admiten archivos PDF")

    suffix = Path(file.filename).suffix
    tmp_path = Path(tempfile.mkstemp(suffix=suffix)[1])
    try:
        content = await file.read()
        tmp_path.write_bytes(content)
        result = validate_pdf(tmp_path)
        result.source = file.filename
        assign_issue_ids(result)
        validation_id = save_validation_record(db, user, result)
        result.validation_id = str(validation_id)
        return result.to_dict()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/validate/slides")
def validate_slides_url(
    body: SlidesValidateRequest,
    creds: Credentials = Depends(get_google_credentials),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    presentation_id = extract_presentation_id(body.url_or_id)
    display_name = assert_google_slides_file(creds, presentation_id)
    result = validate_slides(presentation_id, credentials=creds)
    result.source = display_name
    assign_issue_ids(result)
    validation_id = save_validation_record(db, user, result)
    result.validation_id = str(validation_id)

    total_slides = result.total_slides or 0
    all_slide_numbers = list(range(1, total_slides + 1)) if total_slides > 0 else sorted(
        {issue.slide_number for issue in result.issues}
    )
    if all_slide_numbers:
        threading.Thread(
            target=warm_slide_thumbnails,
            args=(creds, presentation_id, all_slide_numbers),
            daemon=True,
        ).start()

    response = result.to_dict()
    if result.fixable_count > 0:
        fixer = SlidesFixer(credentials=creds)
        working_id, working_url = fixer.create_working_copy(presentation_id)
        response["working_presentation_id"] = working_id
        response["working_presentation_url"] = working_url

    return response


@router.post("/fix")
def fix_presentation(
    body: FixRequest,
    creds: Credentials = Depends(get_google_credentials),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fixer = SlidesFixer(credentials=creds)

    requested_ids = set(body.issue_ids)
    fix_issues = [
        issue_from_fix_input(issue.model_dump())
        for issue in body.issues
        if issue.issue_id in requested_ids
    ]
    if not fix_issues:
        raise HTTPException(status_code=400, detail="No hay correcciones aplicables para los errores seleccionados")

    try:
        fix_result = fixer.fix(
            body.presentation_id,
            issues=fix_issues,
            mode=body.mode,
            original_presentation_id=body.original_presentation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HttpError as exc:
        raise HTTPException(status_code=400, detail=parse_google_http_error(exc)) from exc

    record = FixRecord(
        user_id=user.id,
        source_presentation_id=fix_result.source_presentation_id,
        fixed_presentation_id=fix_result.fixed_presentation_id,
        fixed_url=fix_result.fixed_url,
        fixes_applied=fix_result.fixes_applied,
        result_json=json.dumps(fix_result.to_dict(), ensure_ascii=False),
    )
    db.add(record)
    db.commit()

    return fix_result.to_dict()


@router.post("/export")
def export_presentation(
    body: ExportRequest,
    creds: Credentials = Depends(get_google_credentials),
):
    fixer = SlidesFixer(credentials=creds)
    export_path, mime_type = fixer.export(body.presentation_id, body.format)
    return FileResponse(
        export_path,
        media_type=mime_type,
        filename=export_path.name,
    )


@router.get("/history")
def validation_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    records = (
        db.query(ValidationRecord)
        .filter(ValidationRecord.user_id == user.id)
        .order_by(ValidationRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "source": r.source,
            "source_type": r.source_type,
            "total_slides": r.total_slides,
            "grave_count": r.grave_count,
            "posible_count": r.posible_count,
            "passed": r.passed,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/history/{validation_id}")
def get_validation(
    record: ValidationRecord = Depends(get_user_validation_record),
):
    data = dict(record.result)
    data["validation_id"] = str(record.id)
    if not data.get("presentation_id") and record.presentation_id:
        data["presentation_id"] = record.presentation_id
    if not data.get("source_type"):
        data["source_type"] = record.source_type
    return data


@router.get("/history/{validation_id}/report.pdf")
def download_report_pdf(
    record: ValidationRecord = Depends(get_user_validation_record),
):
    pdf_path = generate_report_pdf(record.result, record.id)
    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)


@router.get("/slides/{presentation_id}/thumbnail/{slide_number}")
def slide_thumbnail(
    presentation_id: str,
    slide_number: int,
    creds: Credentials = Depends(get_google_credentials),
):
    image_path = get_slide_thumbnail(creds, presentation_id, slide_number)
    return FileResponse(image_path, media_type="image/png")
