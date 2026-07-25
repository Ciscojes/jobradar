"""add durable worker queues and heartbeat

Revision ID: 20260724_0008
Revises: 20260723_0007
Create Date: 2026-07-24 19:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0008"
down_revision: Union[str, Sequence[str], None] = "20260723_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_oferta_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_oferta_id"], ["user_ofertas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_outbox_id", "notification_outbox", ["id"])
    op.create_index("ix_notification_outbox_status", "notification_outbox", ["status"])
    op.create_index(
        "ix_notification_outbox_available_at",
        "notification_outbox",
        ["available_at"],
    )
    op.create_index(
        "ix_notification_outbox_user_oferta_id",
        "notification_outbox",
        ["user_oferta_id"],
        unique=True,
    )

    op.create_table(
        "manual_sync_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manual_sync_jobs_id", "manual_sync_jobs", ["id"])
    op.create_index("ix_manual_sync_jobs_user_id", "manual_sync_jobs", ["user_id"])
    op.create_index("ix_manual_sync_jobs_status", "manual_sync_jobs", ["status"])
    op.create_index(
        "ix_manual_sync_jobs_available_at",
        "manual_sync_jobs",
        ["available_at"],
    )

    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("worker_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("manual_jobs_processed", sa.Integer(), nullable=False),
        sa.Column("notifications_processed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_heartbeats_id", "worker_heartbeats", ["id"])
    op.create_index(
        "ix_worker_heartbeats_worker_name",
        "worker_heartbeats",
        ["worker_name"],
        unique=True,
    )
    op.create_index(
        "ix_worker_heartbeats_last_seen_at",
        "worker_heartbeats",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_worker_heartbeats_last_seen_at", table_name="worker_heartbeats")
    op.drop_index("ix_worker_heartbeats_worker_name", table_name="worker_heartbeats")
    op.drop_index("ix_worker_heartbeats_id", table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")

    op.drop_index("ix_manual_sync_jobs_available_at", table_name="manual_sync_jobs")
    op.drop_index("ix_manual_sync_jobs_status", table_name="manual_sync_jobs")
    op.drop_index("ix_manual_sync_jobs_user_id", table_name="manual_sync_jobs")
    op.drop_index("ix_manual_sync_jobs_id", table_name="manual_sync_jobs")
    op.drop_table("manual_sync_jobs")

    op.drop_index("ix_notification_outbox_user_oferta_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_available_at", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_id", table_name="notification_outbox")
    op.drop_table("notification_outbox")
