"""pickup_point: structured address fields + comment

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pickup_points", sa.Column("city", sa.String(64), nullable=True))
    op.add_column("pickup_points", sa.Column("street", sa.String(128), nullable=True))
    op.add_column("pickup_points", sa.Column("building", sa.String(32), nullable=True))
    op.add_column("pickup_points", sa.Column("comment", sa.Text, nullable=True))
    op.alter_column("pickup_points", "work_hours", type_=sa.String(256))


def downgrade() -> None:
    op.drop_column("pickup_points", "city")
    op.drop_column("pickup_points", "street")
    op.drop_column("pickup_points", "building")
    op.drop_column("pickup_points", "comment")
    op.alter_column("pickup_points", "work_hours", type_=sa.String(128))
