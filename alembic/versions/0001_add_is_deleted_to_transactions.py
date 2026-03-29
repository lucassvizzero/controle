"""add is_deleted to transactions

Revision ID: 0001
Revises:
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('transactions', 'is_deleted')
