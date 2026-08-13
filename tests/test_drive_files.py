import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.drive_files import assert_google_slides_file, GOOGLE_SLIDES_MIME


def test_assert_google_slides_file_rejects_pdf():
    drive = MagicMock()
    drive.files().get().execute.return_value = {
        "id": "abc",
        "name": "informe.pdf",
        "mimeType": "application/pdf",
    }
    with patch("src.services.drive_files.build", return_value=drive):
        with pytest.raises(HTTPException) as exc:
            assert_google_slides_file(MagicMock(), "abc")
    assert exc.value.status_code == 400
    assert "no es una presentación" in exc.value.detail


def test_assert_google_slides_file_accepts_slides():
    drive = MagicMock()
    drive.files().get().execute.return_value = {
        "id": "abc",
        "name": "presentacion",
        "mimeType": GOOGLE_SLIDES_MIME,
    }
    with patch("src.services.drive_files.build", return_value=drive):
        name = assert_google_slides_file(MagicMock(), "abc")
    assert name == "presentacion"
