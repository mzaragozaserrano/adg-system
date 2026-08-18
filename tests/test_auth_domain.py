import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Settings
from src.auth.security import is_allowed_email


def test_is_allowed_email_adgravity():
    assert is_allowed_email("lauza.zaragoza@adgravity.com")


def test_is_allowed_email_rejects_other_domains():
    assert not is_allowed_email("user@gmail.com")
    assert not is_allowed_email("user@adgmediagroup.com")


def test_is_allowed_email_specific_allowlist():
    with patch("src.auth.security.settings") as mock_settings:
        mock_settings.resolved_allowed_email_domains = ["adgravity.com"]
        mock_settings.resolved_allowed_emails = ["miguelzaragozaserrano@gmail.com"]
        assert is_allowed_email("miguelzaragozaserrano@gmail.com")
        assert is_allowed_email("MiguelZaragozaSerrano@gmail.com")
        assert not is_allowed_email("otro@gmail.com")


def test_resolved_allowed_email_domains_default():
    settings = Settings()
    assert settings.resolved_allowed_email_domains == ["adgravity.com"]


def test_resolved_allowed_email_domains_multiple():
    settings = Settings(allowed_email_domains="adgravity.com, example.org")
    assert settings.resolved_allowed_email_domains == ["adgravity.com", "example.org"]


def test_resolved_allowed_emails():
    settings = Settings(allowed_emails="uno@example.com, Dos@Example.org")
    assert settings.resolved_allowed_emails == ["uno@example.com", "dos@example.org"]
