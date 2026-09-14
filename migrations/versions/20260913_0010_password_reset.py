"""add secure password reset tokens

Revision ID: 20260913_0010
Revises: 20260818_0009
Create Date: 2026-09-13 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260913_0010"
down_revision: Union[str, Sequence[str], None] = "20260818_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "auth_version" not in user_columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0")
            )
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("auth_version", server_default=None)

    if "password_reset_tokens" not in set(inspector.get_table_names()):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"])
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index(
            "ix_password_reset_tokens_token_hash",
            "password_reset_tokens",
            ["token_hash"],
            unique=True,
        )
        op.create_index(
            "ix_password_reset_tokens_expires_at",
            "password_reset_tokens",
            ["expires_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("auth_version")
