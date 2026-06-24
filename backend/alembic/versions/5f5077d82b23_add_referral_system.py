"""add_referral_system

Revision ID: 5f5077d82b23
Revises: 8a9b0c1d2e3f
Create Date: 2026-06-24 17:55:34.673678

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f5077d82b23'
down_revision: str | None = '8a9b0c1d2e3f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('referral_links',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('donor_id', sa.BigInteger(), nullable=False),
    sa.Column('recipient_id', sa.BigInteger(), nullable=False),
    sa.Column('welcome_paid', sa.Boolean(), nullable=False),
    sa.Column('purchases_rewarded', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['donor_id'], ['users.id'], name=op.f('fk_referral_links_donor_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], name=op.f('fk_referral_links_recipient_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_referral_links')),
    sa.UniqueConstraint('recipient_id', name=op.f('uq_referral_links_recipient_id'))
    )
    op.create_index(op.f('ix_referral_links_donor_id'), 'referral_links', ['donor_id'], unique=False)

    op.add_column('users', sa.Column('referral_code', sa.String(length=16), nullable=True))
    op.add_column('users', sa.Column('referrer_id', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('is_channel_member', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('referral_slots', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('referral_slots_used', sa.Integer(), server_default='0', nullable=False))

    # Unique constraint и FK — не поддерживаются SQLite ALTER TABLE, применяются только на PostgreSQL.
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.create_unique_constraint(op.f('uq_users_referral_code'), 'users', ['referral_code'])
        op.create_foreign_key(op.f('fk_users_referrer_id_users'), 'users', 'users', ['referrer_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.drop_constraint(op.f('fk_users_referrer_id_users'), 'users', type_='foreignkey')
        op.drop_constraint(op.f('uq_users_referral_code'), 'users', type_='unique')

    op.drop_column('users', 'referral_slots_used')
    op.drop_column('users', 'referral_slots')
    op.drop_column('users', 'is_channel_member')
    op.drop_column('users', 'referrer_id')
    op.drop_column('users', 'referral_code')
    op.drop_index(op.f('ix_referral_links_donor_id'), table_name='referral_links')
    op.drop_table('referral_links')
