import random
import time
from typing import Any, Callable

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings
from src.slides.auth import get_google_credentials


def generate_slides_requests(llm_json_data: dict[str, Any]) -> list[dict]:
    requests = []
    for key, value in llm_json_data.items():
        requests.append(
            {
                "replaceAllText": {
                    "containsText": {
                        "text": f"{{{{{key}}}}}",
                        "matchCase": True,
                    },
                    "replaceText": str(value),
                }
            }
        )
    return requests


def with_exponential_backoff(
    func: Callable,
    max_retries: int = 5,
    base_delay: float = 1.0,
) -> Any:
    for attempt in range(max_retries):
        try:
            return func()
        except HttpError as e:
            if e.resp.status not in (429, 500, 503) or attempt == max_retries - 1:
                raise
            delay = base_delay * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)
    return None


class SlidesRenderer:
    def __init__(self) -> None:
        creds = get_google_credentials()
        self._drive = build("drive", "v3", credentials=creds)
        self._slides = build("slides", "v1", credentials=creds)

    def clone_template(self, presentation_name: str) -> str:
        body: dict[str, Any] = {"name": presentation_name}
        if settings.google_drive_folder_id:
            body["parents"] = [settings.google_drive_folder_id]

        def _copy():
            return (
                self._drive.files()
                .copy(fileId=settings.google_template_file_id, body=body)
                .execute()
            )

        copied = with_exponential_backoff(_copy)
        return copied["id"]

    def inject_data(self, presentation_id: str, data: dict[str, Any]) -> None:
        requests = generate_slides_requests(data)
        if not requests:
            return

        body = {"requests": requests}

        def _batch_update():
            return (
                self._slides.presentations()
                .batchUpdate(presentationId=presentation_id, body=body)
                .execute()
            )

        with_exponential_backoff(_batch_update)

    def get_presentation_url(self, presentation_id: str) -> str:
        return f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    def render(self, presentation_name: str, data: dict[str, Any]) -> str:
        if not settings.google_template_file_id:
            raise ValueError("GOOGLE_TEMPLATE_FILE_ID no configurado en .env")
        presentation_id = self.clone_template(presentation_name)
        self.inject_data(presentation_id, data)
        return self.get_presentation_url(presentation_id)
