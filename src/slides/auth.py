from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from config.settings import settings


def get_google_credentials(scopes: list[str] | None = None) -> Credentials:
    scopes = scopes or settings.google_scopes
    creds: Credentials | None = None
    token_path = settings.google_token_path
    credentials_path = settings.google_credentials_path

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"No se encontró {credentials_path}. "
                    "Descarga credentials.json desde Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), scopes
            )
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


def credentials_from_dict(data: dict, scopes: list[str] | None = None) -> Credentials:
    scopes = scopes or settings.google_scopes
    return Credentials.from_authorized_user_info(data, scopes)
