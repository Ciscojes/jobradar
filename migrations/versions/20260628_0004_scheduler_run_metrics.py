"""scheduler run metrics

Revision ID: 20260628_0004
Revises: 20260628_0003
Create Date: 2026-06-28 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_0004"
down_revision: Union[str, Sequence[str], None] = "20260628_0003"
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
    if _table_exists("scraper_runs"):
        _add_column_if_missing("scraper_runs", sa.Column("duration_seconds", sa.Integer(), nullable=True))
        _add_column_if_missing("scraper_runs", sa.Column("new_offers", sa.Integer(), nullable=True))


def downgrade() -> None:
    pass
