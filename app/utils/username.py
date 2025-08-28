from __future__ import annotations


def tg_username(telegram_id: int) -> str:
    """Generate Marzban username from Telegram ID."""
    return f"tg_{telegram_id}"
