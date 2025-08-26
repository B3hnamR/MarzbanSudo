from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    marzban_username: Mapped[str] = mapped_column(String(191), unique=True, index=True)
    subscription_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="active")

    expire_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True, nullable=True)
    data_limit_bytes: Mapped[int] = mapped_column(BigInteger)

    last_usage_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    last_usage_ratio: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    last_notified_usage_threshold: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    last_notified_expiry_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(191))
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="IRR")
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    data_limit_bytes: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))

    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="IRR")
    provider: Mapped[str] = mapped_column(String(32), default="manual_transfer")
    provider_ref: Mapped[Optional[str]] = mapped_column(String(191), nullable=True)
    receipt_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(191), unique=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    provisioned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)

    status: Mapped[str] = mapped_column(String(32))
    payload_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(32))  # admin|user|system
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
