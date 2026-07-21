"""initial schema: demographic_zones and scenario_history

Baseline migration reflecting the schema previously created by
Base.metadata.create_all(). For a database that ALREADY has these tables,
run `alembic stamp head` (do NOT run upgrade). For a fresh database, run
`alembic upgrade head`.

Revision ID: 0001
Revises:
Create Date: 2026-07-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demographic_zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("zone_name", sa.String(), nullable=False),
        sa.Column("min_radius_km", sa.Float(), nullable=False),
        sa.Column("max_radius_km", sa.Float(), nullable=False),
        sa.Column("base_population", sa.Integer(), nullable=False),
        sa.Column("students_pct", sa.Float(), nullable=False),
        sa.Column("families_pct", sa.Float(), nullable=False),
        sa.Column("retirees_pct", sa.Float(), nullable=False),
        sa.Column("summary_text", sa.String(), nullable=False),
        sa.Column("indicator", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_demographic_zones_id", "demographic_zones", ["id"])
    op.create_index("ix_demographic_zones_zone_name", "demographic_zones", ["zone_name"])

    op.create_table(
        "scenario_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("municipality_name", sa.String(length=120), nullable=False),
        sa.Column("business_subcategory", sa.String(length=160), nullable=False),
        sa.Column("radius_km", sa.Float(), nullable=False),
        sa.Column("predicted_monthly_net_revenue", sa.Float(), nullable=True),
        sa.Column("predicted_risk_class", sa.String(length=32), nullable=True),
        sa.Column("predicted_feasibility_score", sa.Float(), nullable=True),
        sa.Column("recommendation_label", sa.String(length=120), nullable=True),
        sa.Column("decision_confidence_score", sa.Float(), nullable=True),
        sa.Column("prediction_confidence_score", sa.Float(), nullable=True),
        sa.Column("demand_pressure_index", sa.Float(), nullable=True),
        sa.Column("competition_pressure_index", sa.Float(), nullable=True),
        sa.Column("median_monthly_lease_cost", sa.Float(), nullable=True),
        sa.Column("data_reliability_note", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_history_id", "scenario_history", ["id"])
    op.create_index(
        "ix_scenario_history_scenario_id", "scenario_history", ["scenario_id"], unique=True
    )
    op.create_index(
        "ix_scenario_history_municipality_name", "scenario_history", ["municipality_name"]
    )
    op.create_index(
        "ix_scenario_history_business_subcategory", "scenario_history", ["business_subcategory"]
    )


def downgrade() -> None:
    op.drop_table("scenario_history")
    op.drop_table("demographic_zones")
