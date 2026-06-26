"""add is_demo to catalog tables

Revision ID: a1b2c3d4e5f6
Revises: 5f5077d82b23
Create Date: 2026-06-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "5f5077d82b23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("categories", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("banners", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("faq_items", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("pickup_points", sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("pickup_points", "is_demo")
    op.drop_column("faq_items", "is_demo")
    op.drop_column("banners", "is_demo")
    op.drop_column("categories", "is_demo")
    op.drop_column("products", "is_demo")
