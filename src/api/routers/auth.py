import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config.settings import settings
from src.api.deps import get_current_user
from src.api.schemas import UserResponse
from src.auth.google_oauth import build_google_auth_url, exchange_google_code, frontend_callback_url
from src.auth.security import create_access_token, credentials_from_encrypted
from src.db.models import User, get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google")
def google_login():
    state = secrets.token_urlsafe(32)
    return RedirectResponse(build_google_auth_url(state))


@router.get("/google/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    user_info, encrypted_token = exchange_google_code(code, state)
    email = user_info["email"]
    user = db.query(User).filter(User.email == email).first()
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

    user.google_token_encrypted = encrypted_token
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return RedirectResponse(frontend_callback_url(token))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, email=user.email, name=user.name, picture=user.picture)


@router.get("/google/picker-config")
def google_picker_config(user: User = Depends(get_current_user)):
    if not settings.google_api_key or not settings.google_app_id:
        raise HTTPException(
            status_code=503,
            detail="Google Picker no configurado. Define GOOGLE_API_KEY y GOOGLE_APP_ID en .env.",
        )
    if not user.google_token_encrypted:
        raise HTTPException(status_code=400, detail="Cuenta Google no vinculada")

    creds = credentials_from_encrypted(user.google_token_encrypted)
    if not creds.token:
        raise HTTPException(status_code=400, detail="No se pudo obtener token de Google")

    return {
        "access_token": creds.token,
        "api_key": settings.google_api_key,
        "app_id": settings.google_app_id,
        "client_id": settings.google_client_id,
    }


@router.post("/logout")
def logout():
    return {"ok": True}
