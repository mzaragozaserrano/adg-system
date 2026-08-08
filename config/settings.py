from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    google_template_file_id: str = ""
    google_drive_folder_id: str = ""
    google_credentials_path: Path = PROJECT_ROOT / "credentials.json"
    google_token_path: Path = PROJECT_ROOT / "token.json"
    uploads_dir: Path = PROJECT_ROOT / "uploads"
    output_dir: Path = PROJECT_ROOT / "output"
    template_schema_path: Path = PROJECT_ROOT / "schemas" / "template_schema.json"
    system_prompt_path: Path = PROJECT_ROOT / "prompts" / "system_prompt.txt"

    google_scopes: list[str] = [
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/drive.file",
    ]


settings = Settings()
