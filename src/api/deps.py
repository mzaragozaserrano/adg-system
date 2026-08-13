import json
from pathlib import Path

from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from src.auth.security import decode_access_token
from src.db.models import User, get_db


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No autenticado")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


def save_validation_record(db: Session, user: User, result) -> int:
    from src.db.models import ValidationRecord

    record = ValidationRecord(
        user_id=user.id,
        source=result.source,
        source_type=result.source_type,
        presentation_id=result.presentation_id,
        total_slides=result.total_slides,
        grave_count=result.grave_count,
        posible_count=result.posible_count,
        passed=result.passed,
        result_json=json.dumps(result.to_dict(), ensure_ascii=False),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.id


def _issue_stable_suffix(issue, index: int) -> str:
    text_start = (issue.text_range or {}).get("start", 0)
    object_id = issue.object_id or f"idx{index}"
    return f"{issue.slide_number}-{object_id}-{text_start}-{issue.category}"


def assign_issue_ids(result, id_prefix: str | None = None) -> None:
    prefix = id_prefix or result.presentation_id or Path(result.source).stem if result.source_type == "pdf" else "slides"
    for index, issue in enumerate(result.issues):
        issue.issue_id = f"{prefix}-{_issue_stable_suffix(issue, index)}"
