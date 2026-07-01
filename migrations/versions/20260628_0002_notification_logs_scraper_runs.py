"""notification logs and scraper runs

Revision ID: 20260628_0002
Revises: 20260628_0001
Create Date: 2026-06-28 21:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260628_0002"
down_revision: Union[str, Sequence[str], None] = "20260628_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _table_exists("notification_logs"):
        op.create_table(
            "notification_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("alert_id", sa.Integer(), nullable=True),
            sa.Column("job_offer_id", sa.Integer(), nullable=True),
            sa.Column("channel", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["alert_id"], ["alertas.id"]),
            sa.ForeignKeyConstraint(["job_offer_id"], ["ofertas.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notification_logs_id"), "notification_logs", ["id"], unique=False)
        op.create_index(op.f("ix_notification_logs_user_id"), "notification_logs", ["user_id"], unique=False)
        op.create_index(op.f("ix_notification_logs_alert_id"), "notification_logs", ["alert_id"], unique=False)
        op.create_index(op.f("ix_notification_logs_job_offer_id"), "notification_logs", ["job_offer_id"], unique=False)

    if not _table_exists("scraper_runs"):
        op.create_table(
            "scraper_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("offers_found", sa.Integer(), nullable=True),
            sa.Column("new_offers", sa.Integer(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_scraper_runs_id"), "scraper_runs", ["id"], unique=False)


def downgrade() -> None:
    if _table_exists("scraper_runs"):
        op.drop_table("scraper_runs")
    if _table_exists("notification_logs"):
        op.drop_table("notification_logs")
