"""add is_unit and unit_label to products

Revision ID: b6c6a25b092b
Revises: a7b8c9d0e1f2
Create Date: 2026-06-22 17:53:21.719840

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c6a25b092b'
down_revision: str | None = 'a7b8c9d0e1f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('products', sa.Column('is_unit', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('products', sa.Column('unit_label', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'unit_label')
    op.drop_column('products', 'is_unit')
