from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

GOOGLE_SCOPES_READONLY = [
    "https://www.googleapis.com/auth/presentations.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

GOOGLE_SCOPES_WRITE = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]

GOOGLE_SCOPES_USERINFO = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

GOOGLE_SCOPES_FULL = GOOGLE_SCOPES_USERINFO + GOOGLE_SCOPES_READONLY + GOOGLE_SCOPES_WRITE


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_root: Path = PROJECT_ROOT
    uploads_dir: Path = PROJECT_ROOT / "uploads"
    exports_dir: Path = PROJECT_ROOT / "exports"
    manual_identidad_path: Path = PROJECT_ROOT / "docs" / "reference" / "manual_identidad_corporativa.pdf"

    google_credentials_path: Path = PROJECT_ROOT / "credentials.json"
    google_token_path: Path = PROJECT_ROOT / "token.json"
    google_scopes: list[str] = GOOGLE_SCOPES_READONLY

    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'validador.db'}"
    secret_key: str = "change-me-in-production"
    allowed_email_domains: str = "adgravity.com"

    @property
    def resolved_allowed_email_domains(self) -> list[str]:
        domains = [
            domain.strip().lower()
            for domain in self.allowed_email_domains.split(",")
            if domain.strip()
        ]
        return domains or ["adgravity.com"]

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    google_api_key: str = ""
    google_app_id: str = ""

    frontend_url: str = "http://localhost:5173"
    api_url: str = "http://localhost:8000"
    cors_origins: str = ""

    access_token_expire_minutes: int = 60 * 24 * 7
    token_encryption_key: str = ""

    @property
    def google_scopes_write(self) -> list[str]:
        return GOOGLE_SCOPES_WRITE

    def resolved_cors_origins(self) -> list[str]:
        origins = {
            self.frontend_url.rstrip("/"),
            "http://localhost:5173",
            "http://localhost:3000",
        }
        for origin in self.cors_origins.split(","):
            cleaned = origin.strip().rstrip("/")
            if cleaned:
                origins.add(cleaned)
        return sorted(origins)


settings = Settings()
