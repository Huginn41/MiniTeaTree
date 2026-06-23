"""set bonus_max_payment_pct to 99 in shop_settings

Revision ID: 8a9b0c1d2e3f
Revises: 7f4debae03a7
Create Date: 2026-06-23 21:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8a9b0c1d2e3f"
down_revision: str | None = "7f4debae03a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE shop_settings SET bonus_max_payment_pct = 99 "
            "WHERE id = 1 AND bonus_max_payment_pct = 50"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE shop_settings SET bonus_max_payment_pct = 50 "
            "WHERE id = 1 AND bonus_max_payment_pct = 99"
        )
    )
