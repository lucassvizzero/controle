"""add monthly_balances and monthly_savings tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'monthly_balances',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('saldo_inicial', sa.DECIMAL(15, 2), nullable=False, server_default='0'),
        sa.Column('saldo_final', sa.DECIMAL(15, 2), nullable=False, server_default='0'),
        sa.Column('saldo_inicial_manual', sa.Boolean(), server_default='false'),
        sa.Column('saldo_final_manual', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'idx_monthly_balance_user_year_month',
        'monthly_balances',
        ['user_id', 'year', 'month'],
        unique=True,
    )

    op.create_table(
        'monthly_savings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('total_guardado', sa.DECIMAL(15, 2), nullable=False, server_default='0'),
        sa.Column('is_manual', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'idx_monthly_savings_user_year_month',
        'monthly_savings',
        ['user_id', 'year', 'month'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table('monthly_savings')
    op.drop_table('monthly_balances')
