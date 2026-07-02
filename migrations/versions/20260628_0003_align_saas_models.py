"""align saas models

Revision ID: 20260628_0003
Revises: 20260628_0002
Create Date: 2026-06-28 21:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_0003"
down_revision: Union[str, Sequence[str], None] = "20260628_0002"
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


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    if _table_exists("alertas"):
        _add_column_if_missing("alertas", sa.Column("categoria", sa.String(), nullable=True))
        _add_column_if_missing("alertas", sa.Column("salario_minimo", sa.Integer(), nullable=True))
        _add_column_if_missing("alertas", sa.Column("fuente", sa.String(), nullable=True))
        _add_column_if_missing("alertas", sa.Column("updated_at", sa.DateTime(), nullable=True))

    if _table_exists("notification_logs"):
        _add_column_if_missing("notification_logs", sa.Column("alert_id", sa.Integer(), nullable=True))
        _add_column_if_missing("notification_logs", sa.Column("job_offer_id", sa.Integer(), nullable=True))
        _add_column_if_missing("notification_logs", sa.Column("channel", sa.String(), nullable=True))
        _add_column_if_missing("notification_logs", sa.Column("message", sa.Text(), nullable=True))
        _create_index_if_missing("notification_logs", "ix_notification_logs_alert_id", ["alert_id"])
        _create_index_if_missing("notification_logs", "ix_notification_logs_job_offer_id", ["job_offer_id"])

    if _table_exists("scraper_runs"):
        _add_column_if_missing("scraper_runs", sa.Column("source", sa.String(), nullable=True))


def downgrade() -> None:
    pass
