"""add bonus_used to orders

Revision ID: 7f4debae03a7
Revises: 2a3b4c5d6e7f
Create Date: 2026-06-23 20:42:06.579550

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f4debae03a7'
down_revision: str | None = '2a3b4c5d6e7f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('orders', sa.Column(
        'bonus_used',
        sa.Numeric(precision=10, scale=2),
        server_default=sa.text('0'),
        nullable=False,
    ))


def downgrade() -> None:
    op.drop_column('orders', 'bonus_used')
