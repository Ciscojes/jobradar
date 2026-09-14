"""scope scraper runs to users

Revision ID: 20260913_0011
Revises: 20260913_0010
Create Date: 2026-09-13 12:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260913_0011"
down_revision: Union[str, Sequence[str], None] = "20260913_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("scraper_runs")}
    if "user_id" not in columns:
        with op.batch_alter_table("scraper_runs") as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    foreign_keys = inspector.get_foreign_keys("scraper_runs")
    indexes = {index["name"] for index in inspector.get_indexes("scraper_runs")}
    has_user_foreign_key = any(
        key.get("constrained_columns") == ["user_id"]
        and key.get("referred_table") == "users"
        for key in foreign_keys
    )
    if not has_user_foreign_key:
        with op.batch_alter_table("scraper_runs") as batch_op:
            batch_op.create_foreign_key(
                "fk_scraper_runs_user_id_users", "users", ["user_id"], ["id"]
            )
    if "ix_scraper_runs_user_id" not in indexes:
        op.create_index("ix_scraper_runs_user_id", "scraper_runs", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("scraper_runs") as batch_op:
        batch_op.drop_index("ix_scraper_runs_user_id")
        batch_op.drop_constraint("fk_scraper_runs_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
