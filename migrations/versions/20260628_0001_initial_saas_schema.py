"""initial saas schema

Revision ID: 20260628_0001
Revises:
Create Date: 2026-06-28 20:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_0001"
down_revision: Union[str, Sequence[str], None] = None
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


def upgrade() -> None:
    if not _table_exists("ofertas"):
        op.create_table(
            "ofertas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("titulo", sa.String(), nullable=False),
            sa.Column("empresa", sa.String(), nullable=False),
            sa.Column("ubicacion", sa.String(), nullable=False),
            sa.Column("modalidad", sa.String(), nullable=True),
            sa.Column("salario", sa.String(), nullable=True),
            sa.Column("descripcion", sa.Text(), nullable=True),
            sa.Column("enlace", sa.String(), nullable=False),
            sa.Column("fuente", sa.String(), nullable=False),
            sa.Column("estado", sa.String(), nullable=True),
            sa.Column("fecha_publicacion", sa.String(), nullable=True),
            sa.Column("creado_en", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ofertas_id"), "ofertas", ["id"], unique=False)
        op.create_index(op.f("ix_ofertas_enlace"), "ofertas", ["enlace"], unique=True)

    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("nombre", sa.String(), nullable=True),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    if not _table_exists("alertas"):
        op.create_table(
            "alertas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("termino", sa.String(), nullable=False),
            sa.Column("ubicacion", sa.String(), nullable=True),
            sa.Column("categoria", sa.String(), nullable=True),
            sa.Column("salario_minimo", sa.Integer(), nullable=True),
            sa.Column("modalidad", sa.String(), nullable=True),
            sa.Column("fuente", sa.String(), nullable=True),
            sa.Column("activo", sa.Boolean(), nullable=True),
            sa.Column("creado_en", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_alertas_id"), "alertas", ["id"], unique=False)
        op.create_index(op.f("ix_alertas_user_id"), "alertas", ["user_id"], unique=False)
    elif not _column_exists("alertas", "user_id"):
        with op.batch_alter_table("alertas") as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
            batch_op.create_index(op.f("ix_alertas_user_id"), ["user_id"], unique=False)

    if not _table_exists("user_ofertas"):
        op.create_table(
            "user_ofertas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("oferta_id", sa.Integer(), nullable=False),
            sa.Column("alerta_id", sa.Integer(), nullable=True),
            sa.Column("estado", sa.String(), nullable=True),
            sa.Column("matched_at", sa.DateTime(), nullable=True),
            sa.Column("notified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["alerta_id"], ["alertas.id"]),
            sa.ForeignKeyConstraint(["oferta_id"], ["ofertas.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "oferta_id", "alerta_id", name="uq_user_oferta_alerta"),
        )
        op.create_index(op.f("ix_user_ofertas_id"), "user_ofertas", ["id"], unique=False)
        op.create_index(op.f("ix_user_ofertas_user_id"), "user_ofertas", ["user_id"], unique=False)
        op.create_index(op.f("ix_user_ofertas_oferta_id"), "user_ofertas", ["oferta_id"], unique=False)
        op.create_index(op.f("ix_user_ofertas_alerta_id"), "user_ofertas", ["alerta_id"], unique=False)

    if not _table_exists("notification_channels"):
        op.create_table(
            "notification_channels",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(), nullable=False),
            sa.Column("destination", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notification_channels_id"), "notification_channels", ["id"], unique=False)
        op.create_index(op.f("ix_notification_channels_user_id"), "notification_channels", ["user_id"], unique=False)


def downgrade() -> None:
    for table_name in ("notification_channels", "user_ofertas", "alertas", "users", "ofertas"):
        if _table_exists(table_name):
            op.drop_table(table_name)
