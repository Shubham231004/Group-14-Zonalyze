"""add Clerk user ownership to scenario history

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenario_history",
        sa.Column("user_id", sa.String(length=191), nullable=True),
    )
    op.create_index(
        "ix_scenario_history_user_id",
        "scenario_history",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_scenario_history_user_id", table_name="scenario_history")
    op.drop_column("scenario_history", "user_id")
