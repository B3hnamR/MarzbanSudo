from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250829_01_wallet'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # users.balance
    op.add_column('users', sa.Column('balance', sa.Numeric(12, 2), nullable=False, server_default='0'))
    # wallet_topups
    op.create_table(
        'wallet_topups',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(8), nullable=False, server_default='IRR'),
        sa.Column('status', sa.String(32), nullable=False, index=True, server_default='pending'),
        sa.Column('receipt_file_id', sa.String(255), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('admin_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
    )
    # settings
    op.create_table(
        'settings',
        sa.Column('key', sa.String(191), primary_key=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade():
    op.drop_table('settings')
    op.drop_table('wallet_topups')
    op.drop_column('users', 'balance')
