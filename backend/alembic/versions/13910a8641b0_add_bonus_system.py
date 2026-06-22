"""add_bonus_system

Revision ID: 13910a8641b0
Revises: d7cc6f4412fa
Create Date: 2026-06-22 23:05:38.396603

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '13910a8641b0'
down_revision: str | None = 'd7cc6f4412fa'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'shop_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bonus_max_payment_pct', sa.Integer(), nullable=False, server_default='50'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_shop_settings')),
    )
    op.create_table(
        'bonus_tiers',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('min_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('cashback_pct', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bonus_tiers')),
    )
    op.create_table(
        'bonus_transactions',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('order_id', sa.BigInteger(), nullable=True),
        sa.Column('delta', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=64), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_bonus_transactions_order_id_orders'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bonus_transactions_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bonus_transactions')),
    )
    op.create_index(op.f('ix_bonus_transactions_user_id'), 'bonus_transactions', ['user_id'], unique=False)
    op.add_column('users', sa.Column('bonus_balance', sa.Numeric(precision=12, scale=2), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'bonus_balance')
    op.drop_index(op.f('ix_bonus_transactions_user_id'), table_name='bonus_transactions')
    op.drop_table('bonus_transactions')
    op.drop_table('bonus_tiers')
    op.drop_table('shop_settings')
