"""user profile fields for instant recommendations

Revision ID: 20260702_0006
Revises: 20260701_0005
Create Date: 2026-07-02 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260702_0006"
down_revision: Union[str, Sequence[str], None] = "20260701_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    _add_column_if_missing("users", sa.Column("puesto_deseado", sa.String(), nullable=True))
    _add_column_if_missing(
        "users",
        sa.Column("ubicacion_preferida", sa.String(), nullable=True, server_default="Cualquiera"),
    )
    _add_column_if_missing(
        "users",
        sa.Column("modalidad_preferida", sa.String(), nullable=True, server_default="Cualquiera"),
    )
    _add_column_if_missing("users", sa.Column("nivel_experiencia", sa.String(), nullable=True))
    _add_column_if_missing("users", sa.Column("bio", sa.Text(), nullable=True))


def downgrade() -> None:
    for column_name in ("bio", "nivel_experiencia", "modalidad_preferida", "ubicacion_preferida", "puesto_deseado"):
        if _column_exists("users", column_name):
            op.drop_column("users", column_name)
