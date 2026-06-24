"""add tbank_payment_id to orders

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa

revision = 'g7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('tbank_payment_id', sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'tbank_payment_id')
