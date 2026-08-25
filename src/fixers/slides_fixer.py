import json
import uuid
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from config.settings import settings
from src.integrations.google.clients import build_drive_client, build_slides_client
from src.services.presentation_cache import invalidate_presentation_cache
from src.validators.color_utils import hex_to_rgb_normalized
from src.validators.models import FixResult, ValidationIssue


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


def parse_google_http_error(exc: HttpError) -> str:
    raw = ""
    try:
        content = exc.content.decode("utf-8") if isinstance(exc.content, bytes) else exc.content
        payload = json.loads(content)
        raw = str(payload.get("error", {}).get("message") or "")
    except Exception:
        raw = str(exc)
    lowered = raw.lower()
    if "font" in lowered:
        return (
            "Google Slides no pudo aplicar la fuente corporativa. "
            "Vuelve a pulsar Reintentar; si persiste, abre la copia de trabajo y cambia la fuente a Helvetica Neue."
        )
    if "range" in lowered or "index" in lowered:
        return "Google Slides rechazó el rango de texto al aplicar la corrección."
    if raw:
        first_line = raw.split("\n", 1)[0].strip()
        if len(first_line) > 220:
            first_line = first_line[:217] + "..."
        return f"No se pudo aplicar la corrección: {first_line}"
    return "No se pudo aplicar la corrección en Google Slides"


def text_range_spec(text_range: dict | None) -> dict[str, Any]:
    if not text_range:
        return {"type": "ALL"}
    start = int(text_range.get("start", 0))
    end = int(text_range.get("end", 0))
    if end <= start:
        return {"type": "ALL"}
    return {
        "type": "FIXED_RANGE",
        "startIndex": start,
        "endIndex": end,
    }


def cell_location_from_range(text_range: dict | None) -> dict[str, int] | None:
    if not text_range:
        return None
    if "rowIndex" not in text_range or "columnIndex" not in text_range:
        return None
    return {
        "rowIndex": int(text_range["rowIndex"]),
        "columnIndex": int(text_range["columnIndex"]),
    }


class SlidesFixer:
    def __init__(self, credentials: Credentials) -> None:
        self._credentials = credentials
        self._slides = build_slides_client(credentials)
        self._drive = build_drive_client(credentials)

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
        font_families = [
            str(issue.fix_payload.get("font_family"))
            for issue in fixable
            if issue.fix_type == "font_family" and issue.fix_payload and issue.fix_payload.get("font_family")
        ]
        dummy_ids: list[str] = []
        try:
            if font_families:
                dummy_ids = self._preload_fonts(target_id, font_families)
            if requests:
                try:
                    self._slides.presentations().batchUpdate(
                        presentationId=target_id,
                        body={"requests": requests},
                    ).execute()
                except HttpError as exc:
                    raise ValueError(parse_google_http_error(exc)) from exc
                invalidate_presentation_cache(target_id)
        finally:
            self._delete_objects(target_id, dummy_ids)

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

    def _preload_fonts(self, presentation_id: str, font_families: list[str]) -> list[str]:
        unique = [family for family in dict.fromkeys(font_families) if family]
        if not unique:
            return []
        try:
            presentation = self._slides.presentations().get(
                presentationId=presentation_id,
                fields="slides.objectId",
            ).execute()
        except HttpError:
            return []
        slides = presentation.get("slides")
        if not isinstance(slides, list) or not slides:
            return []
        page_id = slides[0]["objectId"]
        dummy_ids: list[str] = []
        requests: list[dict[str, Any]] = []
        for family in unique:
            dummy_id = f"adgFontLoad{uuid.uuid4().hex[:10]}"
            dummy_ids.append(dummy_id)
            requests.extend(
                [
                    {
                        "createShape": {
                            "objectId": dummy_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": page_id,
                                "size": {
                                    "width": {"magnitude": 1, "unit": "PT"},
                                    "height": {"magnitude": 1, "unit": "PT"},
                                },
                                "transform": {
                                    "scaleX": 1,
                                    "scaleY": 1,
                                    "translateX": 0,
                                    "translateY": 0,
                                    "unit": "EMU",
                                },
                            },
                        }
                    },
                    {
                        "insertText": {
                            "objectId": dummy_id,
                            "text": "A",
                        }
                    },
                    {
                        "updateTextStyle": {
                            "objectId": dummy_id,
                            "style": {
                                "fontFamily": family,
                                "weightedFontFamily": {"fontFamily": family, "weight": 400},
                            },
                            "fields": "fontFamily,weightedFontFamily",
                            "textRange": {"type": "ALL"},
                        }
                    },
                ]
            )
        try:
            self._slides.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": requests},
            ).execute()
        except HttpError:
            return []
        return dummy_ids

    def _delete_objects(self, presentation_id: str, object_ids: list[str]) -> None:
        if not object_ids:
            return
        try:
            self._slides.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": [{"deleteObject": {"objectId": object_id}} for object_id in object_ids]},
            ).execute()
        except HttpError:
            return

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
        text_range = issue.text_range
        fields: list[str] = []
        style: dict[str, Any] = {}

        if issue.fix_type == "font_family":
            family = issue.fix_payload["font_family"]
            style["fontFamily"] = family
            style["weightedFontFamily"] = {
                "fontFamily": family,
                "weight": issue.fix_payload.get("weight", 400),
            }
            fields.extend(["fontFamily", "weightedFontFamily"])
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
                    "rgbColor": hex_to_rgb_normalized(issue.fix_payload["color"]),
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
                                    "rgbColor": hex_to_rgb_normalized(issue.fix_payload["color"]),
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
                                    "rgbColor": hex_to_rgb_normalized(issue.fix_payload["color"]),
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

        update: dict[str, Any] = {
            "objectId": issue.object_id,
            "textRange": text_range_spec(text_range),
            "style": style,
            "fields": ",".join(fields),
        }
        cell_location = cell_location_from_range(text_range)
        if cell_location:
            update["cellLocation"] = cell_location
        return {"updateTextStyle": update}

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
