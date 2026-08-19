"""add persistent alert scans and shared rate limits

Revision ID: 20260818_0009
Revises: 20260724_0008
Create Date: 2026-08-18 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260818_0009"
down_revision: Union[str, Sequence[str], None] = "20260724_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_scan_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alertas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_scan_jobs_id", "alert_scan_jobs", ["id"])
    op.create_index("ix_alert_scan_jobs_alert_id", "alert_scan_jobs", ["alert_id"])
    op.create_index("ix_alert_scan_jobs_status", "alert_scan_jobs", ["status"])
    op.create_index("ix_alert_scan_jobs_available_at", "alert_scan_jobs", ["available_at"])
    op.create_index("ix_alert_scan_jobs_dedupe_key", "alert_scan_jobs", ["dedupe_key"], unique=True)

    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("window_id", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "key_hash", "window_id", name="uq_rate_limit_bucket"),
    )
    op.create_index("ix_rate_limit_buckets_id", "rate_limit_buckets", ["id"])

    with op.batch_alter_table("worker_heartbeats") as batch_op:
        batch_op.add_column(
            sa.Column("alert_jobs_processed", sa.Integer(), nullable=False, server_default="0")
        )
    with op.batch_alter_table("worker_heartbeats") as batch_op:
        batch_op.alter_column("alert_jobs_processed", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("worker_heartbeats") as batch_op:
        batch_op.drop_column("alert_jobs_processed")
    op.drop_index("ix_rate_limit_buckets_id", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
    op.drop_index("ix_alert_scan_jobs_dedupe_key", table_name="alert_scan_jobs")
    op.drop_index("ix_alert_scan_jobs_available_at", table_name="alert_scan_jobs")
    op.drop_index("ix_alert_scan_jobs_status", table_name="alert_scan_jobs")
    op.drop_index("ix_alert_scan_jobs_alert_id", table_name="alert_scan_jobs")
    op.drop_index("ix_alert_scan_jobs_id", table_name="alert_scan_jobs")
    op.drop_table("alert_scan_jobs")
