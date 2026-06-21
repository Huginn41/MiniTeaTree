"""site_about: таблица содержимого страницы О нас

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_about",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("banner_image_path", sa.String(512), nullable=True),
        sa.Column("title", sa.String(128), server_default="Чайное Дерево", nullable=False),
        sa.Column("description_html", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_site_about"),
    )


def downgrade() -> None:
    op.drop_table("site_about")
