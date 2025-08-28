from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def rials(amount: int | float | Decimal) -> str:
    d = Decimal(str(amount)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    s = f"{d:,}"
    return f"{s} ریال"
