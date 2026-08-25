import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from config.settings import settings
from src.api.deps import get_current_user, get_google_credentials
from src.api.schemas import UserResponse
from src.auth.google_oauth import (
    build_google_auth_url,
    dump_oauth_session,
    exchange_google_code,
    frontend_callback_url,
    load_oauth_session,
    persist_google_token,
)
from src.auth.security import (
    create_access_token,
    create_user_session,
    decode_access_token,
    decrypt_token,
    revoke_user_session,
)
from src.db.models import User, get_db

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "adg_oauth_state"


def _cookie_kwargs() -> dict:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.google_redirect_uri.startswith("https://"),
        "max_age": 600,
        "path": "/",
    }


def _oauth_redirect(url: str, state: str, code_verifier: str) -> RedirectResponse:
    response = RedirectResponse(url)
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        dump_oauth_session(state, code_verifier),
        **_cookie_kwargs(),
    )
    return response


@router.get("/google")
def google_login(consent: bool = False):
    state = secrets.token_urlsafe(32)
    url, verifier = build_google_auth_url(state, force_consent=consent)
    return _oauth_redirect(url, state, verifier)


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    raw_cookie = request.cookies.get(_OAUTH_STATE_COOKIE)
    if not raw_cookie:
        raise HTTPException(status_code=400, detail="Sesión OAuth inválida. Vuelve a iniciar sesión.")
    session = load_oauth_session(raw_cookie)
    if session.get("state") != state:
        raise HTTPException(status_code=400, detail="Sesión OAuth inválida. Vuelve a iniciar sesión.")

    user_info, token_data = exchange_google_code(code, session.get("verifier") or "")
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
        retry_state = secrets.token_urlsafe(32)
        url, verifier = build_google_auth_url(
            retry_state,
            force_consent=True,
            login_hint=email,
        )
        return _oauth_redirect(url, retry_state, verifier)

    user.google_token_encrypted = merged_encrypted
    db.commit()
    db.refresh(user)

    token, jti, expires_at = create_access_token(user.id, user.email)
    create_user_session(db, user.id, jti, expires_at)
    response = RedirectResponse(frontend_callback_url(token))
    response.delete_cookie(_OAUTH_STATE_COOKIE, path="/")
    return response


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
def logout(
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            if jti:
                revoke_user_session(db, jti)
        except Exception:
            pass
    return {"ok": True}
