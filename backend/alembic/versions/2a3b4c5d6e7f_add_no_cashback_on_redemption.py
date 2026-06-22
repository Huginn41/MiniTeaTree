"""add bonus_no_cashback_on_redemption to shop_settings

Revision ID: 2a3b4c5d6e7f
Revises: 13910a8641b0
Create Date: 2026-06-23 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = '2a3b4c5d6e7f'
down_revision: str | None = '13910a8641b0'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        'shop_settings',
        sa.Column(
            'bonus_no_cashback_on_redemption',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )


def downgrade() -> None:
    op.drop_column('shop_settings', 'bonus_no_cashback_on_redemption')
