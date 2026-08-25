import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.settings import GOOGLE_SCOPES_FULL, settings


def _fernet() -> Fernet:
    key = settings.token_encryption_key
    if not key:
        derived = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(derived)
    elif len(key) != 44:
        derived = hashlib.sha256(key.encode()).digest()
        key = base64.urlsafe_b64encode(derived)
    return Fernet(key)


def encrypt_token(token_data: dict) -> str:
    return _fernet().encrypt(json.dumps(token_data).encode()).decode()


def decrypt_token(encrypted: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(encrypted.encode()).decode())
    except InvalidToken as exc:
        raise ValueError("Token de Google inválido o corrupto") from exc


def credentials_from_encrypted(encrypted: str, scopes: list[str] | None = None) -> Credentials:
    data = decrypt_token(encrypted)
    creds = Credentials.from_authorized_user_info(data, scopes or GOOGLE_SCOPES_FULL)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def create_access_token(user_id: int, email: str) -> tuple[str, str, datetime]:
    jti = secrets.token_hex(32)
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expire, "jti": jti}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return token, jti, expire


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Token de sesión inválido") from exc


def create_user_session(db: Session, user_id: int, jti: str, expires_at: datetime) -> None:
    from src.db.models import UserSession
    session = UserSession(user_id=user_id, jti=jti, expires_at=expires_at)
    db.add(session)
    db.commit()


def revoke_user_session(db: Session, jti: str) -> bool:
    from src.db.models import UserSession
    session = db.query(UserSession).filter(UserSession.jti == jti).first()
    if not session or session.is_revoked:
        return False
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return True


def is_session_valid(db: Session, jti: str) -> bool:
    from src.db.models import UserSession
    session = db.query(UserSession).filter(UserSession.jti == jti).first()
    if not session:
        return False
    if session.is_revoked:
        return False
    if session.is_expired:
        return False
    return True


def is_allowed_email(email: str) -> bool:
    normalized_email = email.lower().strip()
    if normalized_email in settings.resolved_allowed_emails:
        return True

    allowed_domains = settings.resolved_allowed_email_domains
    if not allowed_domains and not settings.resolved_allowed_emails:
        return True
    if not allowed_domains:
        return False
    return any(normalized_email.endswith(f"@{domain}") for domain in allowed_domains)


def allowed_email_hint() -> str:
    parts: list[str] = []
    if settings.resolved_allowed_email_domains:
        parts.append(
            "dominios: " + ", ".join(f"@{domain}" for domain in settings.resolved_allowed_email_domains)
        )
    if settings.resolved_allowed_emails:
        parts.append("correos: " + ", ".join(settings.resolved_allowed_emails))
    return "; ".join(parts)
