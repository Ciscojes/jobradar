"""notification log channel fields and scraper run matches

Revision ID: 20260701_0005
Revises: 20260628_0004
Create Date: 2026-07-01 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260701_0005"
down_revision: Union[str, Sequence[str], None] = "20260628_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    # notification_logs necesita apuntar al canal y al match concreto (user_ofertas)
    # que las notificaciones nuevas usan (ver app/services/notifications.py).
    if _table_exists("notification_logs"):
        _add_column_if_missing(
            "notification_logs", sa.Column("user_oferta_id", sa.Integer(), nullable=True)
        )
        _add_column_if_missing(
            "notification_logs", sa.Column("channel_id", sa.Integer(), nullable=True)
        )
        _add_column_if_missing(
            "notification_logs", sa.Column("channel_type", sa.String(), nullable=True)
        )
        _add_column_if_missing(
            "notification_logs", sa.Column("destination", sa.String(), nullable=True)
        )
        _add_column_if_missing(
            "notification_logs", sa.Column("error_message", sa.Text(), nullable=True)
        )
        _add_column_if_missing(
            "notification_logs", sa.Column("sent_at", sa.DateTime(), nullable=True)
        )

        with op.batch_alter_table("notification_logs") as batch_op:
            batch_op.create_foreign_key(
                "fk_notification_logs_user_oferta_id",
                "user_ofertas",
                ["user_oferta_id"],
                ["id"],
            )
            batch_op.create_foreign_key(
                "fk_notification_logs_channel_id",
                "notification_channels",
                ["channel_id"],
                ["id"],
            )
            # "channel" y "message" quedan como columnas legacy opcionales
            batch_op.alter_column("channel", existing_type=sa.String(), nullable=True)

        op.create_index(
            op.f("ix_notification_logs_user_oferta_id"),
            "notification_logs",
            ["user_oferta_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_notification_logs_channel_id"),
            "notification_logs",
            ["channel_id"],
            unique=False,
        )

    if _table_exists("scraper_runs"):
        _add_column_if_missing("scraper_runs", sa.Column("new_matches", sa.Integer(), nullable=True))


def downgrade() -> None:
    if _table_exists("notification_logs"):
        with op.batch_alter_table("notification_logs") as batch_op:
            batch_op.drop_constraint("fk_notification_logs_channel_id", type_="foreignkey")
            batch_op.drop_constraint("fk_notification_logs_user_oferta_id", type_="foreignkey")
            batch_op.alter_column("channel", existing_type=sa.String(), nullable=False)
        op.drop_index(op.f("ix_notification_logs_channel_id"), table_name="notification_logs")
        op.drop_index(op.f("ix_notification_logs_user_oferta_id"), table_name="notification_logs")
        op.drop_column("notification_logs", "sent_at")
        op.drop_column("notification_logs", "error_message")
        op.drop_column("notification_logs", "destination")
        op.drop_column("notification_logs", "channel_type")
        op.drop_column("notification_logs", "channel_id")
        op.drop_column("notification_logs", "user_oferta_id")

    if _table_exists("scraper_runs"):
        op.drop_column("scraper_runs", "new_matches")
