"""unified order status

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем новые поля
    op.add_column("orders", sa.Column("status", sa.String(32), nullable=True))
    op.add_column("orders", sa.Column("payment_link", sa.String(512), nullable=True))
    op.add_column("orders", sa.Column("tracking_link", sa.String(512), nullable=True))

    # Мигрируем данные: переносим статусы в единое поле
    op.execute("""
        UPDATE orders SET status =
            CASE
                WHEN status_delivery = 'delivered' THEN 'delivered'
                WHEN status_delivery = 'cancelled' OR status_payment = 'cancelled' THEN 'cancelled'
                WHEN status_delivery = 'shipping' THEN 'in_delivery'
                WHEN status_delivery IN ('awaiting_delivery_payment', 'delivery_paid') THEN 'awaiting_payment'
                WHEN status_delivery = 'manager_contacted' THEN 'awaiting_payment'
                ELSE 'new'
            END
    """)

    # Делаем поле NOT NULL после заполнения
    op.alter_column("orders", "status", nullable=False)

    # Удаляем старые CHECK-констрейнты
    op.drop_constraint("status_payment_valid", "orders", type_="check")
    op.drop_constraint("status_delivery_valid", "orders", type_="check")

    # Удаляем старые колонки
    op.drop_column("orders", "status_payment")
    op.drop_column("orders", "status_delivery")

    # Добавляем новый CHECK-констрейнт
    op.create_check_constraint(
        "status_valid",
        "orders",
        "status IN ('new','assembling','ready','awaiting_payment','in_delivery','at_pvz','delivered','cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint("status_valid", "orders", type_="check")
    op.add_column("orders", sa.Column("status_payment", sa.String(32), nullable=False, server_default="pending"))
    op.add_column("orders", sa.Column("status_delivery", sa.String(32), nullable=False, server_default="new"))
    op.execute("""
        UPDATE orders SET
            status_delivery = CASE WHEN status = 'delivered' THEN 'delivered'
                                   WHEN status = 'cancelled' THEN 'cancelled'
                                   WHEN status = 'in_delivery' THEN 'shipping'
                                   WHEN status = 'at_pvz' THEN 'shipping'
                                   WHEN status = 'awaiting_payment' THEN 'awaiting_delivery_payment'
                                   ELSE 'new' END,
            status_payment = CASE WHEN status = 'delivered' THEN 'paid' ELSE 'pending' END
    """)
    op.drop_column("orders", "status")
    op.drop_column("orders", "payment_link")
    op.drop_column("orders", "tracking_link")
