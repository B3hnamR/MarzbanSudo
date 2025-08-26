from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


def _parse_csv_ints(raw: str) -> List[int]:
    ids: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            pass
    return ids


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "production")
    tz: str = os.getenv("TZ", "UTC")

    marzban_base_url: str = os.getenv("MARZBAN_BASE_URL", "")
    marzban_admin_username: str = os.getenv("MARZBAN_ADMIN_USERNAME", "")
    marzban_admin_password: str = os.getenv("MARZBAN_ADMIN_PASSWORD", "")

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_admin_ids: List[int] = _parse_csv_ints(os.getenv("TELEGRAM_ADMIN_IDS", ""))

    db_url: str = os.getenv("DB_URL", "")

    notify_usage_thresholds: str = os.getenv("NOTIFY_USAGE_THRESHOLDS", "0.7,0.9")
    notify_expiry_days: str = os.getenv("NOTIFY_EXPIRY_DAYS", "3,1,0")

    sub_domain_preferred: str = os.getenv("SUB_DOMAIN_PREFERRED", "irsub.fun")

    log_chat_id: str = os.getenv("LOG_CHAT_ID", "")

    cleanup_expired_after_days: int = int(os.getenv("CLEANUP_EXPIRED_AFTER_DAYS", "7"))
    pending_order_autocancel_hours: int = int(os.getenv("PENDING_ORDER_AUTOCANCEL_HOURS", "12"))
    rate_limit_user_msg_per_min: int = int(os.getenv("RATE_LIMIT_USER_MSG_PER_MIN", "20"))
    receipt_retention_days: int = int(os.getenv("RECEIPT_RETENTION_DAYS", "30"))


settings = Settings()
