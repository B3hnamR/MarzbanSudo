from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250826_000001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("marzban_username", sa.String(length=191), nullable=False),
        sa.Column("subscription_token", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("expire_at", sa.DateTime(), nullable=True),
        sa.Column("data_limit_bytes", sa.BigInteger(), nullable=False),
        sa.Column("last_usage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_usage_ratio", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("last_notified_usage_threshold", sa.Numeric(5, 4), nullable=True),
        sa.Column("last_notified_expiry_day", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("telegram_id"),
        sa.UniqueConstraint("marzban_username"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"]) 
    op.create_index("ix_users_marzban_username", "users", ["marzban_username"]) 
    op.create_index("ix_users_expire_at", "users", ["expire_at"]) 
    op.create_index("ix_users_status", "users", ["status"]) 

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=191), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="IRR"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("data_limit_bytes", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("template_id"),
    )
    op.create_index("ix_plans_template_id", "plans", ["template_id"]) 
    op.create_index("ix_plans_is_active", "plans", ["is_active"]) 

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="IRR"),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="manual_transfer"),
        sa.Column("provider_ref", sa.String(length=191), nullable=True),
        sa.Column("receipt_file_path", sa.Text(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=191), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("provisioned_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_orders_user_id_status_created_at", "orders", ["user_id", "status", "created_at"]) 

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_raw", sa.Text(), nullable=True),
        sa.Column("signature_valid", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("order_id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("meta", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("transactions")
    op.drop_index("ix_orders_user_id_status_created_at", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_plans_is_active", table_name="plans")
    op.drop_index("ix_plans_template_id", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_expire_at", table_name="users")
    op.drop_index("ix_users_marzban_username", table_name="users")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
