from __future__ import annotations

import asyncio


def test_notifications_without_token() -> None:
    # When TELEGRAM_BOT_TOKEN/LOG_CHAT_ID are not set, notifications should return False (no crash)
    from app.services.notifications import notify_user, notify_log

    ok_user = asyncio.run(notify_user(telegram_id=123456789, text="test message"))
    ok_log = asyncio.run(notify_log(text="operational log"))

    assert ok_user is False
    assert ok_log is False


def test_plan_text_decimal_formatting() -> None:
    # _plan_text should handle Decimal price and include Toman label when price > 0
    from decimal import Decimal
    from app.db.models import Plan
    from app.bot.handlers.plans import _plan_text

    p = Plan(
        template_id=1,
        title="30D-20GB",
        price=Decimal("1500000"),  # 150000 Toman
        currency="IRR",
        duration_days=30,
        data_limit_bytes=20 * 1024 ** 3,
        description=None,
        is_active=True,
    )

    s = _plan_text(p)
    assert isinstance(s, str)
    assert "تومان" in s  # Toman label should appear when price > 0
