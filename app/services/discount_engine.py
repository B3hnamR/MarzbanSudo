from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple

from sqlalchemy import func, select

from app.db.session import session_scope
from app.db.models import Coupon, CouponRedemption, User


@dataclass
class OrderContext:
    user_id: int
    amount: Decimal
    is_renew: bool = False
    now: datetime = datetime.now(timezone.utc)


@dataclass
class CouponEvalResult:
    valid: bool
    reason: Optional[str] = None
    discount: Decimal = Decimal("0")


def _within_window(now: datetime, start: Optional[datetime], end: Optional[datetime]) -> bool:
    if start and now < start.replace(tzinfo=start.tzinfo or timezone.utc):
        return False
    if end and now > end.replace(tzinfo=end.tzinfo or timezone.utc):
        return False
    return True


def _compute_discount(amount: Decimal, coupon: Coupon) -> Decimal:
    if amount <= 0:
        return Decimal("0")
    if coupon.type == "percent":
        pct = (coupon.value or Decimal("0")) / Decimal("100")
        disc = (amount * pct).quantize(Decimal("0.01"))
    else:  # fixed
        disc = Decimal(coupon.value or 0)
    cap = coupon.cap
    if cap is not None and cap > 0:
        disc = min(disc, cap)
    if disc < 0:
        disc = Decimal("0")
    return disc


async def validate_coupon_for_order(code: str, ctx: OrderContext) -> CouponEvalResult:
    code = (code or "").strip()
    if not code:
        return CouponEvalResult(False, reason="کد خالی است")
    async with session_scope() as session:
        coupon: Optional[Coupon] = await session.scalar(
            select(Coupon).where(Coupon.code == code)
        )
        if not coupon:
            return CouponEvalResult(False, reason="کد نامعتبر است")
        if not coupon.active:
            return CouponEvalResult(False, reason="این کد غیرفعال است")
        now = ctx.now
        if not _within_window(now, coupon.start_at, coupon.end_at):
            return CouponEvalResult(False, reason="این کد در بازه زمانی فعلی معتبر نیست")
        if coupon.min_order_amount and ctx.amount < coupon.min_order_amount:
            return CouponEvalResult(False, reason="مبلغ سفارش کمتر از حداقل لازم برای این کد است")
        # Global usage limits
        if coupon.max_uses is not None:
            total_used = await session.scalar(
                select(func.count(CouponRedemption.id)).where(
                    CouponRedemption.coupon_id == coupon.id,
                    CouponRedemption.status == "applied",
                )
            )
            if (total_used or 0) >= coupon.max_uses:
                return CouponEvalResult(False, reason="سقف استفاده از این کد به پایان رسیده است")
        if coupon.max_uses_per_user is not None:
            user_used = await session.scalar(
                select(func.count(CouponRedemption.id)).where(
                    CouponRedemption.coupon_id == coupon.id,
                    CouponRedemption.user_id == ctx.user_id,
                    CouponRedemption.status == "applied",
                )
            )
            if (user_used or 0) >= coupon.max_uses_per_user:
                return CouponEvalResult(False, reason="سقف استفاده شما برای این کد به پایان رسیده است")
        disc = _compute_discount(ctx.amount, coupon)
        if disc <= 0:
            return CouponEvalResult(False, reason="میزان تخفیف این کد برای سفارش شما صفر است")
        return CouponEvalResult(True, discount=disc)


async def record_redemption(coupon_code: str, user_id: int, order_id: Optional[int], applied_amount: Decimal) -> Tuple[bool, Optional[int]]:
    """Persist a redemption row when an order is submitted/paid.
    Returns (ok, redemption_id)."""
    async with session_scope() as session:
        coupon = await session.scalar(select(Coupon).where(Coupon.code == coupon_code))
        if not coupon:
            return False, None
        red = CouponRedemption(
            coupon_id=coupon.id,
            user_id=user_id,
            order_id=order_id,
            applied_amount=applied_amount,
            status="applied",
        )
        session.add(red)
        await session.flush()
        red_id = red.id
        await session.commit()
        return True, red_id


async def reverse_redemption(redemption_id: int) -> bool:
    async with session_scope() as session:
        red = await session.get(CouponRedemption, redemption_id)
        if not red or red.status != "applied":
            return False
        red.status = "reversed"
        await session.commit()
        return True
