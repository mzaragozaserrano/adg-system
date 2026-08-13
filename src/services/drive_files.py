from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException
from google.oauth2.credentials import Credentials

GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"

MIME_LABELS = {
    "application/pdf": "PDF",
    "application/vnd.google-apps.document": "Google Docs",
    "application/vnd.google-apps.spreadsheet": "Google Sheets",
    "application/vnd.google-apps.form": "Google Forms",
    "application/vnd.google-apps.drawing": "Google Drawing",
}


def assert_google_slides_file(credentials: Credentials, file_id: str) -> str:
    drive = build("drive", "v3", credentials=credentials)
    try:
        metadata = drive.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    except HttpError as exc:
        if exc.resp.status == 404:
            raise HTTPException(status_code=404, detail="No se encontró el archivo en Google Drive") from exc
        raise HTTPException(status_code=400, detail=f"No se pudo acceder al archivo: {exc}") from exc

    mime_type = metadata.get("mimeType", "")
    name = metadata.get("name", file_id)
    if mime_type != GOOGLE_SLIDES_MIME:
        label = MIME_LABELS.get(mime_type, mime_type or "desconocido")
        raise HTTPException(
            status_code=400,
            detail=f"El archivo «{name}» no es una presentación de Google Slides (tipo detectado: {label}).",
        )
    return name
