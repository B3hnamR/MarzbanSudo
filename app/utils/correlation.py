from __future__ import annotations

import uuid
import contextvars

# Task-local correlation id for logging/observability
_cid = contextvars.ContextVar("correlation_id", default="")


def set_correlation_id(value: str | None = None) -> str:
    """Set a correlation id for the current task (generate if not provided)."""
    cid = value or uuid.uuid4().hex
    _cid.set(cid)
    return cid


def get_correlation_id() -> str:
    """Get current correlation id (empty string if not set)."""
    return _cid.get("")


def clear_correlation_id() -> None:
    """Clear current correlation id (sets to empty string)."""
    _cid.set("")
