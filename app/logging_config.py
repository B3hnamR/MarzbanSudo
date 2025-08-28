from __future__ import annotations

import json
import logging
import logging.config
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


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
            payload.update(record.extra)
        return json.dumps(payload, ensure_ascii=False)


def _bool(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def setup_logging() -> None:
    """Configure structured logging based on environment variables.

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

    # Handlers
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "stream": "ext://sys.stdout",
            "formatter": "json" if log_format == "json" else "plain",
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
        }

    # Build dictConfig
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
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
            "httpx": {"level": "INFO"},
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
