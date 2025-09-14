"""
IDPay payment provider stub.

This module is a placeholder for future integration. Implementations should:
- initiate_payment(amount: int, order_id: int, ...) -> str (payment_url)
- verify_callback(params: dict) -> tuple[bool, str] (ok, reference)
"""

from __future__ import annotations


def initiate_payment(*args, **kwargs) -> str:
    raise NotImplementedError("IDPay provider is not implemented yet.")


def verify_callback(*args, **kwargs) -> tuple[bool, str]:
    raise NotImplementedError("IDPay provider callback verification is not implemented yet.")
