from typing import List
from pydantic import BaseModel


class ScenarioHistoryItem(BaseModel):
    scenario_id: str
    saved_at: str
    municipality_name: str
    business_subcategory: str
    radius_km: float

    predicted_monthly_net_revenue: float | None = None
    predicted_risk_class: str | None = None
    predicted_feasibility_score: float | None = None
    recommendation_label: str | None = None
    decision_confidence_score: float | None = None
    prediction_confidence_score: float | None = None

    demand_pressure_index: float | None = None
    competition_pressure_index: float | None = None
    median_monthly_lease_cost: float | None = None

    data_reliability_note: str


class ScenarioHistoryResponse(BaseModel):
    count: int
    scenarios: List[ScenarioHistoryItem]


class ScenarioComparisonItem(BaseModel):
    scenario_id: str
    label: str
    overall_score: float
    revenue_position: int
    risk_position: int
    feasibility_position: int
    confidence_position: int
    key_tradeoff: str


class ScenarioComparisonResponse(BaseModel):
    generated_at: str
    compared_count: int
    best_overall_scenario_id: str | None
    comparison_summary: str
    rankings: List[ScenarioComparisonItem]
