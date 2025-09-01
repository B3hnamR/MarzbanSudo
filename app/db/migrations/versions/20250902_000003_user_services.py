"""
Add user_services table and orders.user_service_id

Revision ID: 20250902_000003_user_services
Revises: 20250829_000002_wallet
Create Date: 2025-09-02 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250902_000003_user_services"
down_revision = "20250829_000002_wallet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_services table
    op.create_table(
        "user_services",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("username", sa.String(length=191), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("last_token", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    # Indexes & constraints for user_services
    op.create_index("ix_user_services_user_id", "user_services", ["user_id"]) 
    op.create_index("ix_user_services_username", "user_services", ["username"], unique=True)
    op.create_index("ix_user_services_status", "user_services", ["status"]) 

    # Add user_service_id to orders
    op.add_column("orders", sa.Column("user_service_id", sa.Integer(), nullable=True))
    op.create_index("ix_orders_user_service_id", "orders", ["user_service_id"]) 
    op.create_foreign_key(
        "fk_orders_user_service_id_user_services",
        "orders",
        "user_services",
        ["user_service_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop FK & index & column from orders
    op.drop_constraint("fk_orders_user_service_id_user_services", "orders", type_="foreignkey")
    op.drop_index("ix_orders_user_service_id", table_name="orders")
    op.drop_column("orders", "user_service_id")

    # Drop user_services table & indexes
    op.drop_index("ix_user_services_status", table_name="user_services")
    op.drop_index("ix_user_services_username", table_name="user_services")
    op.drop_index("ix_user_services_user_id", table_name="user_services")
    op.drop_table("user_services")
