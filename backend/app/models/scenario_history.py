from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class ScenarioHistoryRecord(Base):
    """
    PostgreSQL-backed record for saved Zonalyze scenarios.

    This replaces the temporary JSON file used during the first scenario-history
    prototype. Each row stores the scenario identity plus the key outputs needed
    for history listing and comparison.
    """

    __tablename__ = "scenario_history"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(String(64), unique=True, nullable=False, index=True)
    saved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Clerk user id (JWT `sub`). NULL when auth is disabled — those rows form the
    # shared anonymous history, matching the pre-auth behaviour.
    user_id = Column(String(191), nullable=True, index=True)

    municipality_name = Column(String(120), nullable=False, index=True)
    business_subcategory = Column(String(160), nullable=False, index=True)
    radius_km = Column(Float, nullable=False)

    predicted_monthly_net_revenue = Column(Float, nullable=True)
    predicted_risk_class = Column(String(32), nullable=True)
    predicted_feasibility_score = Column(Float, nullable=True)
    recommendation_label = Column(String(120), nullable=True)
    decision_confidence_score = Column(Float, nullable=True)
    prediction_confidence_score = Column(Float, nullable=True)

    demand_pressure_index = Column(Float, nullable=True)
    competition_pressure_index = Column(Float, nullable=True)
    median_monthly_lease_cost = Column(Float, nullable=True)

    data_reliability_note = Column(Text, nullable=False)
