import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config.settings import settings
from src.api.deps import get_current_user, get_google_credentials
from src.api.schemas import UserResponse
from src.auth.google_oauth import (
    build_google_auth_url,
    exchange_google_code,
    frontend_callback_url,
    persist_google_token,
)
from src.auth.security import create_access_token, credentials_from_encrypted, decrypt_token
from src.db.models import User, get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
def google_login(consent: bool = False):
    state = secrets.token_urlsafe(32)
    return RedirectResponse(build_google_auth_url(state, force_consent=consent))


@router.get("/google/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    user_info, token_data = exchange_google_code(code, state)
    email = user_info["email"]
    user = db.query(User).filter(User.email == email).first()
    existing_encrypted = user.google_token_encrypted if user else None
    if not user:
        user = User(
            email=email,
            name=user_info.get("name", ""),
            picture=user_info.get("picture"),
        )
        db.add(user)
    else:
        user.name = user_info.get("name", user.name)
        user.picture = user_info.get("picture", user.picture)

    merged_encrypted = persist_google_token(token_data, existing_encrypted)

    try:
        merged_data = decrypt_token(merged_encrypted)
    except Exception:
        merged_data = {}

    if not merged_data.get("refresh_token"):
        return RedirectResponse(build_google_auth_url(secrets.token_urlsafe(32), force_consent=True))

    user.google_token_encrypted = merged_encrypted
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return RedirectResponse(frontend_callback_url(token))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, name=user.name, picture=user.picture)


@router.get("/google/picker-config")
def google_picker_config(creds=Depends(get_google_credentials)):
    if not creds.token:
        raise HTTPException(status_code=400, detail="No se pudo obtener token de Google")

    response = {
        "access_token": creds.token,
        "client_id": settings.google_client_id,
    }
    if settings.google_api_key and settings.google_app_id:
        response["api_key"] = settings.google_api_key
        response["app_id"] = settings.google_app_id
    return response


@router.post("/logout")
def logout():
    return {"ok": True}
