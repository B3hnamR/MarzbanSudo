from __future__ import annotations

import logging
import os

import pytest

from app.logging_config import _sanitize_str, _sanitize_obj, setup_logging


def test_sanitize_authorization_bearer_masked() -> None:
    s = "Authorization: Bearer ABCDEFGHIJKLMNOP"
    out = _sanitize_str(s)
    assert "Bearer [REDACTED]" in out


def test_sanitize_access_token_kv_masked() -> None:
    s = '{"access_token":"abc.def.ghi","other":"x"}'
    out = _sanitize_str(s)
    assert '"access_token":"[REDACTED]"' in out


def test_sanitize_sub4me_url_token_masked() -> None:
    s = "https://panel.example.com/sub4me/SECRET123/token/info"
    out = _sanitize_str(s)
    assert "/sub4me/[REDACTED]/token" in out


def test_sanitize_nested_objects() -> None:
    obj = {
        "authorization": "Authorization: Bearer VERYSECRETTOKEN",
        "nested": [
            {"access_token": "abc123"},
            {"subscription_url": "https://p/sub4me/T0KENXYZ/"},
        ],
    }
    out = _sanitize_obj(obj)
    # Access token masked
    assert out["nested"][0]["access_token"].startswith("***") or out["nested"][0]["access_token"] == "[REDACTED]"
    # URL token segment masked
    assert "/sub4me/[REDACTED]/" in out["nested"][1]["subscription_url"]
    # Authorization header masked
    assert "[REDACTED]" in out["authorization"]


def test_httpx_logger_level_warning_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_TO_FILE", "0")
    setup_logging()
    logger = logging.getLogger("httpx")
    assert logger.level == logging.WARNING or logger.getEffectiveLevel() == logging.WARNING

