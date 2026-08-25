import json
from pathlib import Path

from fastapi import Depends, HTTPException, Header
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from src.auth.security import credentials_from_encrypted, decode_access_token, is_session_valid
from src.db.models import User, ValidationRecord, get_db


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

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Sesión expirada o cerrada. Vuelve a iniciar sesión.")
    from datetime import datetime, timezone
    token_exp = payload.get("exp")
    exp_dt = datetime.fromtimestamp(token_exp, tz=timezone.utc) if token_exp else None
    user_id = int(payload["sub"]) if payload.get("sub") else None
    if not is_session_valid(db, jti, user_id=user_id, token_exp=exp_dt):
        raise HTTPException(status_code=401, detail="Sesión expirada o cerrada. Vuelve a iniciar sesión.")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        email = payload.get("email", "")
        if email:
            user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Sesión expirada. Por favor, vuelve a iniciar sesión.",
        )
    return user


def get_google_credentials(user: User = Depends(get_current_user)) -> Credentials:
    if not user.google_token_encrypted:
        raise HTTPException(status_code=400, detail="Cuenta Google no vinculada")
    return credentials_from_encrypted(user.google_token_encrypted)


def get_user_validation_record(
    validation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ValidationRecord:
    record = (
        db.query(ValidationRecord)
        .filter(ValidationRecord.id == validation_id, ValidationRecord.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Validación no encontrada")
    return record


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
