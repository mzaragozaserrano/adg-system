import os
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import GOOGLE_SCOPES_FULL
from src.auth.google_oauth import (
    build_google_auth_url,
    dump_oauth_session,
    load_oauth_session,
    persist_google_token,
)
from src.auth.security import decrypt_token, encrypt_token


def test_oauth_relaxes_token_scope_when_google_returns_previously_granted_scopes():
    assert os.environ.get("OAUTHLIB_RELAX_TOKEN_SCOPE") == "1"


def test_oauth_scopes_do_not_request_redundant_readonly_presentations():
    assert "https://www.googleapis.com/auth/presentations" in GOOGLE_SCOPES_FULL
    assert "https://www.googleapis.com/auth/presentations.readonly" not in GOOGLE_SCOPES_FULL
    assert "https://www.googleapis.com/auth/drive.file" in GOOGLE_SCOPES_FULL


@patch("src.auth.google_oauth.settings")
def test_auth_url_requests_consent_and_account_in_one_trip(mock_settings):
    mock_settings.google_client_id = "client-id.apps.googleusercontent.com"
    mock_settings.google_client_secret = "client-secret"
    mock_settings.google_redirect_uri = "http://localhost:8000/auth/google/callback"

    url, verifier = build_google_auth_url("state-token")
    params = parse_qs(urlparse(url).query)
    prompt = unquote(params.get("prompt", [""])[0])

    assert verifier
    assert "select_account" in prompt
    assert "consent" in prompt
    assert params.get("access_type") == ["offline"]
    assert params.get("state") == ["state-token"]
    assert "include_granted_scopes" not in params


@patch("src.auth.google_oauth.settings")
def test_auth_url_retry_uses_login_hint_without_account_picker(mock_settings):
    mock_settings.google_client_id = "client-id.apps.googleusercontent.com"
    mock_settings.google_client_secret = "client-secret"
    mock_settings.google_redirect_uri = "http://localhost:8000/auth/google/callback"

    url, _verifier = build_google_auth_url(
        "state-token",
        force_consent=True,
        login_hint="miguel@adgravity.com",
    )
    params = parse_qs(urlparse(url).query)

    assert params.get("prompt") == ["consent"]
    assert params.get("login_hint") == ["miguel@adgravity.com"]


def test_persist_google_token_keeps_existing_refresh_token():
    previous = encrypt_token(
        {
            "token": "old-access",
            "refresh_token": "stored-refresh",
            "scopes": [],
        }
    )
    encrypted = persist_google_token(
        {
            "token": "new-access",
            "refresh_token": None,
            "scopes": [],
        },
        previous,
    )
    stored = decrypt_token(encrypted)
    assert stored["token"] == "new-access"
    assert stored["refresh_token"] == "stored-refresh"


def test_persist_google_token_prefers_new_refresh_token():
    previous = encrypt_token({"token": "old", "refresh_token": "old-refresh"})
    encrypted = persist_google_token(
        {"token": "new", "refresh_token": "new-refresh"},
        previous,
    )
    stored = decrypt_token(encrypted)
    assert stored["refresh_token"] == "new-refresh"


def test_oauth_session_cookie_roundtrip():
    token = dump_oauth_session("state-1", "verifier-1")
    loaded = load_oauth_session(token)
    assert loaded["state"] == "state-1"
    assert loaded["verifier"] == "verifier-1"
