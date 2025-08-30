from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250830_000003_order_snapshot"
down_revision = "20250829_000002_wallet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make plan_id nullable to decouple orders from plans
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.alter_column("plan_id", existing_type=sa.Integer(), nullable=True)
        # Snapshot fields
        batch_op.add_column(sa.Column("plan_template_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("plan_title", sa.String(length=191), nullable=True))
        batch_op.add_column(sa.Column("plan_price", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("plan_currency", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("plan_duration_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("plan_data_limit_bytes", sa.BigInteger(), nullable=True))
        # Service lifecycle timestamps
        batch_op.add_column(sa.Column("service_start_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("service_end_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        # Remove snapshot/lifecycle fields
        batch_op.drop_column("service_end_at")
        batch_op.drop_column("service_start_at")
        batch_op.drop_column("plan_data_limit_bytes")
        batch_op.drop_column("plan_duration_days")
        batch_op.drop_column("plan_currency")
        batch_op.drop_column("plan_price")
        batch_op.drop_column("plan_title")
        batch_op.drop_column("plan_template_id")
        # Revert plan_id to NOT NULL (may fail if NULLs exist)
        batch_op.alter_column("plan_id", existing_type=sa.Integer(), nullable=False)
