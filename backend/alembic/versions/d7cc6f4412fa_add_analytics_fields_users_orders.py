"""add_analytics_fields_users_orders

Revision ID: d7cc6f4412fa
Revises: b6c6a25b092b
Create Date: 2026-06-22 18:28:22.320275

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd7cc6f4412fa'
down_revision: str | None = 'b6c6a25b092b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('language_code', sa.String(length=8), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('segment', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('orders', sa.Column('source', sa.String(length=32), server_default=sa.text("'mini_app'"), nullable=False))
    op.add_column('orders', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('cancel_reason', sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'cancel_reason')
    op.drop_column('orders', 'cancelled_at')
    op.drop_column('orders', 'source')

    op.drop_column('users', 'last_seen_at')
    op.drop_column('users', 'notes')
    op.drop_column('users', 'segment')
    op.drop_column('users', 'city')
    op.drop_column('users', 'language_code')
    op.drop_column('users', 'email')
