"""create coupons and coupon_redemptions

Revision ID: 20250920_000004_coupons
Revises: 20250902_000003_user_services
Create Date: 2025-09-20 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250920_000004_coupons'
down_revision = '20250902_000003_user_services'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'coupons',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(length=64), nullable=False, unique=True),
        sa.Column('title', sa.String(length=191), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=16), nullable=False, server_default='percent'),
        sa.Column('value', sa.Numeric(12, 2), nullable=False),
        sa.Column('cap', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=False, server_default='IRR'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('start_at', sa.DateTime(), nullable=True),
        sa.Column('end_at', sa.DateTime(), nullable=True),
        sa.Column('min_order_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('max_uses_per_user', sa.Integer(), nullable=True),
        sa.Column('is_stackable', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_coupons_code', 'coupons', ['code'], unique=True)
    op.create_index('ix_coupons_active', 'coupons', ['active'], unique=False)
    op.create_index('ix_coupons_start_at', 'coupons', ['start_at'], unique=False)
    op.create_index('ix_coupons_end_at', 'coupons', ['end_at'], unique=False)
    op.create_index('ix_coupons_priority', 'coupons', ['priority'], unique=False)

    op.create_table(
        'coupon_redemptions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('coupon_id', sa.Integer(), sa.ForeignKey('coupons.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('applied_amount', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='applied'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_coupon_redemptions_coupon_id', 'coupon_redemptions', ['coupon_id'], unique=False)
    op.create_index('ix_coupon_redemptions_user_id', 'coupon_redemptions', ['user_id'], unique=False)
    op.create_index('ix_coupon_redemptions_order_id', 'coupon_redemptions', ['order_id'], unique=False)
    op.create_index('ix_coupon_redemptions_status', 'coupon_redemptions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_coupon_redemptions_status', table_name='coupon_redemptions')
    op.drop_index('ix_coupon_redemptions_order_id', table_name='coupon_redemptions')
    op.drop_index('ix_coupon_redemptions_user_id', table_name='coupon_redemptions')
    op.drop_index('ix_coupon_redemptions_coupon_id', table_name='coupon_redemptions')
    op.drop_table('coupon_redemptions')

    op.drop_index('ix_coupons_priority', table_name='coupons')
    op.drop_index('ix_coupons_end_at', table_name='coupons')
    op.drop_index('ix_coupons_start_at', table_name='coupons')
    op.drop_index('ix_coupons_active', table_name='coupons')
    op.drop_index('ix_coupons_code', table_name='coupons')
    op.drop_table('coupons')
