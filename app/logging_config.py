from __future__ import annotations

import json
import logging
import logging.config
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


# ================= Sensitive Data Masking ================= #
_TOKEN_RE = re.compile(r"([A-Fa-f0-9]{16,}|[A-Za-z0-9._-]{16,})")
_BEARER_RE = re.compile(r"(Authorization\s*:\s*Bearer\s+)([A-Za-z0-9._-]+)", re.IGNORECASE)
# Match sub4me token in URLs: https://domain/sub4me/<token>/...
_SUB4ME_RE = re.compile(r"(https?://[^/\s]+/sub4me/)([A-Za-z0-9._-]+)(/[^\s\"]*)?", re.IGNORECASE)
# Common JSON-like access_token patterns inside strings
_ACCESS_TOKEN_KV_RE = re.compile(r"(access_token\"?\s*[:=]\s*\"?)([A-Za-z0-9._-]+)", re.IGNORECASE)


def _mask_tail(val: str, keep: int = 4) -> str:
    if not isinstance(val, str):
        return val
    if len(val) <= keep:
        return "[REDACTED]"
    return "***" + val[-keep:]


def _sanitize_str(s: str) -> str:
    if not isinstance(s, str) or not s:
        return s
    # Mask Authorization Bearer tokens
    s = _BEARER_RE.sub(lambda m: m.group(1) + "[REDACTED]", s)
    # Mask sub4me URLs' token segment
    def _sub4me_sub(m: re.Match[str]) -> str:
        prefix = m.group(1)
        token = m.group(2)
        suffix = m.group(3) or ""
        return f"{prefix}[REDACTED]{suffix}"

    s = _SUB4ME_RE.sub(_sub4me_sub, s)
    # Mask explicit access_token-like kv pairs
    s = _ACCESS_TOKEN_KV_RE.sub(lambda m: m.group(1) + "[REDACTED]", s)
    return s


def _sanitize_obj(obj: Any) -> Any:
    # Recursively sanitize dict/list/tuple and strings
    try:
        if isinstance(obj, dict):
            out: Dict[str, Any] = {}
            for k, v in obj.items():
                lk = str(k).lower()
                if lk in {"token", "access_token", "subscription_token"}:
                    out[k] = "[REDACTED]" if not isinstance(v, str) else _mask_tail(v)
                elif lk in {"subscription_url", "url", "authorization", "auth"}:
                    out[k] = _sanitize_str(str(v))
                else:
                    out[k] = _sanitize_obj(v)
            return out
        if isinstance(obj, (list, tuple)):
            t = type(obj)
            return t(_sanitize_obj(v) for v in obj)
        if isinstance(obj, str):
            return _sanitize_str(obj)
    except Exception:
        return obj
    return obj


class SensitiveDataFilter(logging.Filter):
    """A logging filter that masks sensitive data in record message, args, and extra."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            # Sanitize message
            if isinstance(record.msg, str):
                record.msg = _sanitize_str(record.msg)
            # Sanitize args (format values)
            if record.args:
                if isinstance(record.args, tuple):
                    record.args = tuple(_sanitize_obj(a) for a in record.args)
                elif isinstance(record.args, dict):
                    record.args = _sanitize_obj(record.args)
            # Sanitize custom extra payload if present
            if hasattr(record, "extra") and isinstance(record.extra, dict):
                record.extra = _sanitize_obj(record.extra)
        except Exception:
            # Never break logging
            pass
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            # Avoid nesting; merge (already sanitized by filter but sanitize again defensively)
            payload.update(record.extra)
        # Final pass sanitization
        payload = _sanitize_obj(payload)
        return json.dumps(payload, ensure_ascii=False)


def _bool(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def setup_logging() -> None:
    """Configure structured logging with sensitive data masking.

    ENV:
      - APP_ENV: production|staging|development (default: production)
      - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR (default: INFO in prod, DEBUG otherwise)
      - LOG_FORMAT: json|text (default: json in prod, text otherwise)
      - LOG_TO_FILE: 1/0 (default: 1 if logs dir exists)
      - LOG_FILE_PATH: path to log file (default: ./logs/app.log)
    """
    app_env = os.getenv("APP_ENV", "production").lower()
    default_level = "INFO" if app_env == "production" else "DEBUG"
    log_level = os.getenv("LOG_LEVEL", default_level).upper()
    log_format = os.getenv("LOG_FORMAT", "json" if app_env == "production" else "text").lower()

    logs_dir_default = os.path.join(os.getcwd(), "logs")
    log_file_path = os.getenv("LOG_FILE_PATH", os.path.join(logs_dir_default, "app.log"))

    # Decide file logging based on env and actual writability
    env_log_to_file = os.getenv("LOG_TO_FILE")
    log_to_file_default = False
    try:
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        # Probe writability
        with open(log_file_path, "a", encoding="utf-8"):
            pass
        log_to_file_default = True
    except Exception:
        log_to_file_default = False

    log_to_file = _bool(env_log_to_file, log_to_file_default)

    # Formatters
    if log_format == "json":
        console_formatter = JsonFormatter()
        file_formatter = JsonFormatter()
    else:
        fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        console_formatter = logging.Formatter(fmt)
        file_formatter = logging.Formatter(fmt)

    # Filters
    filters: Dict[str, Dict[str, Any]] = {
        "sensitive": {"()": SensitiveDataFilter}
    }

    # Handlers
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "stream": "ext://sys.stdout",
            "formatter": "json" if log_format == "json" else "plain",
            "filters": ["sensitive"],
        }
    }

    if log_to_file:
        # Ensure directory exists (best-effort)
        try:
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        except Exception:
            pass
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "filename": log_file_path,
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 3,
            "encoding": "utf-8",
            "delay": True,
            "formatter": "json" if log_format == "json" else "plain",
            "filters": ["sensitive"],
        }

    # Build dictConfig
    httpx_level = "WARNING" if app_env == "production" else "INFO"

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": filters,
        "formatters": {
            "json": {
                "()": JsonFormatter,
            },
            "plain": {
                "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            },
        },
        "handlers": handlers,
        "root": {
            "level": log_level,
            "handlers": list(handlers.keys()),
        },
        "loggers": {
            # Reduce noise
            "aiogram": {"level": log_level},
            "httpx": {"level": httpx_level},
            "sqlalchemy.engine": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)

    logging.getLogger(__name__).info(
        "logging configured",
        extra={
            "extra": {
                "env": app_env,
                "level": log_level,
                "format": log_format,
                "to_file": log_to_file,
                "file": log_file_path if log_to_file else None,
            }
        },
    )
