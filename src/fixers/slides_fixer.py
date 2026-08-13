from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from config.settings import settings
from src.services.presentation_cache import invalidate_presentation_cache
from src.validators.models import FixResult, ValidationIssue


def _hex_to_rgb_normalized(hex_color: str) -> dict:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return {"red": r, "green": g, "blue": b}


def issue_from_fix_input(data: dict[str, Any]) -> ValidationIssue:
    return ValidationIssue(
        slide_number=0,
        category="",
        message="",
        object_id=data["object_id"],
        text_range=data.get("text_range"),
        fix_type=data["fix_type"],
        fix_payload=data["fix_payload"],
        issue_id=data.get("issue_id"),
    )


class SlidesFixer:
    def __init__(self, credentials: Credentials) -> None:
        self._credentials = credentials
        self._slides = build("slides", "v1", credentials=credentials)
        self._drive = build("drive", "v3", credentials=credentials)

    def create_working_copy(self, presentation_id: str) -> tuple[str, str]:
        source_name = self._get_file_name(presentation_id)
        copy_name = f"{source_name} (ADG corregida)"
        copy_response = self._drive.files().copy(
            fileId=presentation_id,
            body={"name": copy_name},
        ).execute()
        target_id = copy_response["id"]
        return target_id, self._presentation_url(target_id)

    def fix(
        self,
        presentation_id: str,
        issues: list[ValidationIssue],
        mode: str = "in_place",
        original_presentation_id: str | None = None,
    ) -> FixResult:
        fixable = [i for i in issues if i.is_fixable]
        if not fixable:
            raise ValueError("No hay correcciones aplicables para los errores seleccionados")

        target_id = presentation_id
        if mode == "copy":
            if original_presentation_id and presentation_id != original_presentation_id:
                target_id = presentation_id
            else:
                target_id, _ = self.create_working_copy(presentation_id)
        elif mode == "in_place":
            if original_presentation_id and presentation_id == original_presentation_id:
                raise ValueError("No se puede modificar el archivo original")
        else:
            raise ValueError(f"Modo de corrección no soportado: {mode}")

        requests = self._build_requests(fixable)
        if requests:
            self._slides.presentations().batchUpdate(
                presentationId=target_id,
                body={"requests": requests},
            ).execute()
            invalidate_presentation_cache(target_id)

        return FixResult(
            source_presentation_id=original_presentation_id or presentation_id,
            fixed_presentation_id=target_id,
            fixed_url=self._presentation_url(target_id),
            fixes_applied=len(requests),
            issue_ids=[i.issue_id for i in fixable if i.issue_id],
        )

    def _presentation_url(self, presentation_id: str) -> str:
        return f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    def _get_file_name(self, file_id: str) -> str:
        metadata = self._drive.files().get(fileId=file_id, fields="name").execute()
        return metadata.get("name", "Presentación")

    def _build_requests(self, issues: list[ValidationIssue]) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        for issue in issues:
            if not issue.object_id or not issue.fix_type or not issue.fix_payload:
                continue
            request = self._issue_to_request(issue)
            if request:
                requests.append(request)
        return requests

    def _issue_to_request(self, issue: ValidationIssue) -> dict[str, Any] | None:
        text_range = issue.text_range or {"start": 0, "end": 1}
        fields: list[str] = []
        style: dict[str, Any] = {}

        if issue.fix_type == "font_family":
            style["fontFamily"] = issue.fix_payload["font_family"]
            fields.append("fontFamily")
        elif issue.fix_type == "font_weight":
            if issue.fix_payload.get("bold") is True:
                style["bold"] = True
                fields.append("bold")
            elif issue.fix_payload.get("bold") is False:
                style["bold"] = False
                fields.append("bold")
            if "weight" in issue.fix_payload:
                style["weightedFontFamily"] = {
                    "fontFamily": issue.fix_payload.get("font_family", "Helvetica Neue"),
                    "weight": issue.fix_payload["weight"],
                }
                fields.append("weightedFontFamily")
        elif issue.fix_type == "text_color":
            style["foregroundColor"] = {
                "opaqueColor": {
                    "rgbColor": _hex_to_rgb_normalized(issue.fix_payload["color"]),
                }
            }
            fields.append("foregroundColor")
        elif issue.fix_type == "font_size":
            style["fontSize"] = {
                "magnitude": issue.fix_payload["font_size"],
                "unit": "PT",
            }
            fields.append("fontSize")
        elif issue.fix_type == "background_color":
            return {
                "updatePageProperties": {
                    "objectId": issue.object_id,
                    "pageProperties": {
                        "pageBackgroundFill": {
                            "solidFill": {
                                "color": {
                                    "rgbColor": _hex_to_rgb_normalized(issue.fix_payload["color"]),
                                }
                            }
                        }
                    },
                    "fields": "pageBackgroundFill.solidFill.color",
                }
            }
        elif issue.fix_type == "fill_color":
            return {
                "updateShapeProperties": {
                    "objectId": issue.object_id,
                    "shapeProperties": {
                        "shapeBackgroundFill": {
                            "solidFill": {
                                "color": {
                                    "rgbColor": _hex_to_rgb_normalized(issue.fix_payload["color"]),
                                }
                            }
                        }
                    },
                    "fields": "shapeBackgroundFill.solidFill.color",
                }
            }
        else:
            return None

        if not fields:
            return None

        return {
            "updateTextStyle": {
                "objectId": issue.object_id,
                "textRange": {
                    "type": "FIXED_RANGE",
                    "startIndex": text_range["start"],
                    "endIndex": text_range["end"],
                },
                "style": style,
                "fields": ",".join(fields),
            }
        }

    def export(self, presentation_id: str, export_format: str = "pdf") -> tuple[Path, str]:
        mime_map = {
            "pdf": ("application/pdf", ".pdf"),
            "pptx": (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".pptx",
            ),
        }
        if export_format not in mime_map:
            raise ValueError(f"Formato no soportado: {export_format}")

        mime_type, suffix = mime_map[export_format]
        settings.exports_dir.mkdir(parents=True, exist_ok=True)
        export_path = settings.exports_dir / f"{presentation_id}{suffix}"

        request = self._drive.files().export_media(fileId=presentation_id, mimeType=mime_type)
        import io

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        export_path.write_bytes(buffer.getvalue())
        return export_path, mime_type
