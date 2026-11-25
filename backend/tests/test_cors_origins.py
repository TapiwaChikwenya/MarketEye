import pytest
from pydantic import ValidationError

from app.core.config import Settings, parse_cors_origins


def test_json_array_origins_are_not_split_on_the_comma_inside_the_list():
    assert parse_cors_origins('["http://localhost:5173","http://localhost:3000"]') == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


def test_comma_separated_origins_drop_wrapping_quotes():
    assert parse_cors_origins('http://localhost, "http://127.0.0.1:5173"') == [
        "http://localhost",
        "http://127.0.0.1:5173",
    ]


def test_production_rejects_the_dev_compose_placeholder_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "super-secret-key-change-in-production")
    with pytest.raises(ValidationError):
        Settings(
            DATABASE_URL="sqlite+aiosqlite:///:memory:",
            DATABASE_URL_SYNC="sqlite:///:memory:",
        )


def test_development_still_accepts_the_placeholder_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SECRET_KEY", "super-secret-key-change-in-production")
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        DATABASE_URL_SYNC="sqlite:///:memory:",
    )
    assert settings.SECRET_KEY == "super-secret-key-change-in-production"
