"""make user offer matches unique per user and offer

Revision ID: 20260723_0007
Revises: 20260702_0006
Create Date: 2026-07-23 21:15:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_0007"
down_revision: Union[str, Sequence[str], None] = "20260702_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _unique_constraint_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("user_ofertas")
        if constraint.get("name")
    }


def _merge_duplicate_matches() -> None:
    connection = op.get_bind()
    duplicate_groups = connection.execute(
        sa.text(
            """
            SELECT user_id, oferta_id, MIN(id) AS keeper_id
            FROM user_ofertas
            GROUP BY user_id, oferta_id
            HAVING COUNT(*) > 1
            """
        )
    ).mappings()

    for group in duplicate_groups:
        params = {
            "user_id": group["user_id"],
            "oferta_id": group["oferta_id"],
            "keeper_id": group["keeper_id"],
        }
        connection.execute(
            sa.text(
                """
                UPDATE notification_logs
                SET user_oferta_id = :keeper_id
                WHERE user_oferta_id IN (
                    SELECT id FROM user_ofertas
                    WHERE user_id = :user_id
                      AND oferta_id = :oferta_id
                      AND id != :keeper_id
                )
                """
            ),
            params,
        )
        connection.execute(
            sa.text(
                """
                DELETE FROM user_ofertas
                WHERE user_id = :user_id
                  AND oferta_id = :oferta_id
                  AND id != :keeper_id
                """
            ),
            params,
        )


def upgrade() -> None:
    _merge_duplicate_matches()
    op.execute(
        sa.text(
            """
            UPDATE notification_channels
            SET is_active = false
            WHERE type = 'telegram' AND verified_at IS NULL
            """
        )
    )
    constraints = _unique_constraint_names()
    with op.batch_alter_table("user_ofertas") as batch_op:
        if "uq_user_oferta_alerta" in constraints:
            batch_op.drop_constraint("uq_user_oferta_alerta", type_="unique")
        if "uq_user_oferta" not in constraints:
            batch_op.create_unique_constraint("uq_user_oferta", ["user_id", "oferta_id"])


def downgrade() -> None:
    constraints = _unique_constraint_names()
    with op.batch_alter_table("user_ofertas") as batch_op:
        if "uq_user_oferta" in constraints:
            batch_op.drop_constraint("uq_user_oferta", type_="unique")
        if "uq_user_oferta_alerta" not in constraints:
            batch_op.create_unique_constraint(
                "uq_user_oferta_alerta",
                ["user_id", "oferta_id", "alerta_id"],
            )
