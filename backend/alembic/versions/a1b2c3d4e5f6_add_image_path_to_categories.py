"""add image_path to categories

Revision ID: a1b2c3d4e5f6
Revises: 2bc9c5dc3f1e
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "2bc9c5dc3f1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("image_path", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "image_path")
