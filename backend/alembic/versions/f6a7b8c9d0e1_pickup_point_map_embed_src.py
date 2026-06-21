"""pickup_point: add map_embed_src column

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pickup_points", sa.Column("map_embed_src", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("pickup_points", "map_embed_src")
