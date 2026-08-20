import os
from urllib.parse import urlencode

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException
from google_auth_oauthlib.flow import Flow
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from config.settings import GOOGLE_SCOPES_FULL, settings
from src.auth.security import decrypt_token, encrypt_token, allowed_email_hint, is_allowed_email

oauth = OAuth()
_OAUTH_COOKIE_SALT = "adg-oauth-state"
_OAUTH_COOKIE_MAX_AGE = 600

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile " + " ".join(GOOGLE_SCOPES_FULL)},
    )


def _oauth_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt=_OAUTH_COOKIE_SALT)


def dump_oauth_session(state: str, code_verifier: str) -> str:
    return _oauth_serializer().dumps({"state": state, "verifier": code_verifier})


def load_oauth_session(token: str) -> dict:
    try:
        return _oauth_serializer().loads(token, max_age=_OAUTH_COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(
            status_code=400,
            detail="Sesión OAuth inválida. Vuelve a iniciar sesión.",
        ) from exc


def get_oauth_flow() -> Flow:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=503,
            detail="OAuth de Google no configurado. Define GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET.",
        )
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GOOGLE_SCOPES_FULL)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def build_google_auth_url(
    state: str,
    force_consent: bool = False,
    login_hint: str = "",
) -> tuple[str, str]:
    flow = get_oauth_flow()
    if force_consent:
        prompt = "consent"
    else:
        prompt = "select_account consent"
    kwargs: dict = {
        "access_type": "offline",
        "prompt": prompt,
        "state": state,
    }
    if login_hint:
        kwargs["login_hint"] = login_hint
    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url, flow.code_verifier or ""


def _fetch_user_info(access_token: str) -> dict:
    response = httpx.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30.0,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo obtener el perfil de Google: {response.text}",
        )
    return response.json()


def exchange_google_code(code: str, code_verifier: str = "") -> tuple[dict, dict]:
    flow = get_oauth_flow()
    if code_verifier:
        flow.code_verifier = code_verifier
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error al intercambiar código OAuth: {exc}") from exc

    creds = flow.credentials
    if not creds or not creds.token:
        raise HTTPException(status_code=400, detail="No se pudo obtener token de Google")

    user_info = _fetch_user_info(creds.token)
    email = user_info.get("email", "")
    if not email or not is_allowed_email(email):
        raise HTTPException(
            status_code=403,
            detail=f"Cuenta no autorizada. Permitidos: {allowed_email_hint()}",
        )

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or GOOGLE_SCOPES_FULL),
    }
    return user_info, token_data


def persist_google_token(token_data: dict, existing_encrypted: str | None) -> str:
    if not token_data.get("refresh_token") and existing_encrypted:
        previous = decrypt_token(existing_encrypted)
        if previous.get("refresh_token"):
            token_data["refresh_token"] = previous["refresh_token"]
    return encrypt_token(token_data)


def frontend_callback_url(token: str) -> str:
    params = urlencode({"token": token})
    return f"{settings.frontend_url}/auth/callback?{params}"
