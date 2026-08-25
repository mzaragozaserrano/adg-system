import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.fixers.slides_fixer import SlidesFixer
from src.validators.color_utils import hex_to_rgb_normalized
from src.validators.models import ValidationIssue


def test_hex_to_rgb_normalized():
    rgb = hex_to_rgb_normalized("#02445B")
    assert abs(rgb["red"] - 2 / 255) < 0.01
    assert abs(rgb["green"] - 68 / 255) < 0.01
    assert abs(rgb["blue"] - 91 / 255) < 0.01


def test_issue_to_request_text_color():
    fixer = SlidesFixer(credentials=MagicMock())
    issue = ValidationIssue(
        slide_number=1,
        category="color_texto",
        message="test",
        object_id="obj1",
        text_range={"start": 0, "end": 5},
        fix_type="text_color",
        fix_payload={"color": "#02445B"},
    )
    request = fixer._issue_to_request(issue)
    assert request is not None
    assert "updateTextStyle" in request
    assert request["updateTextStyle"]["objectId"] == "obj1"


def test_fix_applies_without_validation():
    fixer = SlidesFixer(credentials=MagicMock())
    fixer._slides = MagicMock()
    fixer._drive = MagicMock()

    issue = ValidationIssue(
        slide_number=1,
        category="color_texto",
        message="test",
        object_id="obj1",
        text_range={"start": 0, "end": 5},
        fix_type="text_color",
        fix_payload={"color": "#02445B"},
        issue_id="issue-1",
    )

    result = fixer.fix(
        "working-copy-id",
        issues=[issue],
        mode="in_place",
        original_presentation_id="original-id",
    )

    fixer._slides.presentations().batchUpdate.assert_called_once()
    assert result.fixed_presentation_id == "working-copy-id"
    assert result.fixes_applied == 1
    assert result.issue_ids == ["issue-1"]
    assert "validation_before" not in result.to_dict()


def test_issue_to_request_font_family():
    fixer = SlidesFixer(credentials=MagicMock())
    issue = ValidationIssue(
        slide_number=1,
        category="tipografía",
        message="test",
        object_id="obj2",
        text_range={"start": 0, "end": 10},
        fix_type="font_family",
        fix_payload={"font_family": "Helvetica Neue"},
    )
    request = fixer._issue_to_request(issue)
    assert request["updateTextStyle"]["style"]["fontFamily"] == "Helvetica Neue"
    assert request["updateTextStyle"]["style"]["weightedFontFamily"] == {
        "fontFamily": "Helvetica Neue",
        "weight": 400,
    }
    assert "weightedFontFamily" in request["updateTextStyle"]["fields"]
    assert request["updateTextStyle"]["textRange"] == {
        "type": "FIXED_RANGE",
        "startIndex": 0,
        "endIndex": 10,
    }


def test_issue_to_request_font_family_uses_all_when_range_invalid():
    fixer = SlidesFixer(credentials=MagicMock())
    issue = ValidationIssue(
        slide_number=1,
        category="tipografía",
        message="test",
        object_id="obj2",
        text_range={"start": 0, "end": 0},
        fix_type="font_family",
        fix_payload={"font_family": "Helvetica Neue"},
    )
    request = fixer._issue_to_request(issue)
    assert request["updateTextStyle"]["textRange"] == {"type": "ALL"}


def test_issue_to_request_includes_table_cell_location():
    fixer = SlidesFixer(credentials=MagicMock())
    issue = ValidationIssue(
        slide_number=1,
        category="tipografía",
        message="test",
        object_id="table1",
        text_range={"start": 0, "end": 5, "rowIndex": 1, "columnIndex": 2},
        fix_type="font_family",
        fix_payload={"font_family": "Helvetica Neue"},
    )
    request = fixer._issue_to_request(issue)
    assert request["updateTextStyle"]["cellLocation"] == {"rowIndex": 1, "columnIndex": 2}


def test_parse_google_http_error_font_message():
    from googleapiclient.errors import HttpError

    from src.fixers.slides_fixer import parse_google_http_error

    response = MagicMock()
    response.status = 400
    response.reason = "Bad Request"
    exc = HttpError(
        response,
        b'{"error": {"message": "Invalid requests[0].updateTextStyle: There was a problem applying the font family."}}',
    )
    message = parse_google_http_error(exc)
    assert "fuente" in message.lower()


def test_font_family_fix_preloads_font_then_updates():
    fixer = SlidesFixer(credentials=MagicMock())
    fixer._slides = MagicMock()
    fixer._drive = MagicMock()
    fixer._slides.presentations().get().execute.return_value = {
        "slides": [{"objectId": "slide1"}]
    }

    issue = ValidationIssue(
        slide_number=1,
        category="tipografía",
        message="test",
        object_id="obj2",
        text_range={"start": 0, "end": 5},
        fix_type="font_family",
        fix_payload={"font_family": "Helvetica Neue"},
        issue_id="issue-font",
    )

    result = fixer.fix(
        "working-copy-id",
        issues=[issue],
        mode="in_place",
        original_presentation_id="original-id",
    )

    assert fixer._slides.presentations().batchUpdate.call_count == 3
    assert result.fixes_applied == 1
    assert result.issue_ids == ["issue-font"]


def test_api_health():
    from fastapi.testclient import TestClient
    from src.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["allowed_email_domains"] == ["adgravity.com"]
    assert body["allowed_emails"] == []
