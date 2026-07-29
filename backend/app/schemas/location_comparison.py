from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class LocationComparisonRequest(BaseModel):
    business_subcategory: str = Field(..., example="Indian Grocery Store")
    base_municipality_name: Optional[str] = Field(default=None, example="Kitchener")
    candidate_municipalities: List[str] = Field(
        default_factory=list,
        description="Municipalities to compare. If empty, the backend uses a safe default sample from the catalog.",
        example=["Kitchener", "Waterloo", "Cambridge", "Guelph", "London"],
    )
    radius_options_km: List[float] = Field(
        default_factory=lambda: [3, 5, 10],
        description="Radius values to compare for each municipality.",
        example=[3, 5, 10],
    )
    max_results: int = Field(default=10, ge=1, le=30)

    @model_validator(mode="after")
    def clean_inputs(self):
        self.candidate_municipalities = [
            " ".join(str(item or "").strip().split())
            for item in self.candidate_municipalities
            if str(item or "").strip()
        ]
        self.radius_options_km = sorted(
            {
                float(radius)
                for radius in self.radius_options_km
                if radius is not None and 1 <= float(radius) <= 25
            }
        ) or [5]
        return self


class LocationComparisonItem(BaseModel):
    rank: int
    municipality_name: str
    radius_km: float
    business_subcategory: str
    predicted_monthly_net_revenue: float
    predicted_feasibility_score: float
    predicted_risk_class: str
    recommendation: str
    high_risk_probability: float
    competition_pressure_index: float
    demand_pressure_index: float
    rent_pressure_index: float
    reachable_population_estimate: float
    estimated_monthly_lease_cost: float
    estimated_monthly_operating_cost: float
    decision_score: float
    strengths: List[str] = []
    concerns: List[str] = []
    data_notes: List[str] = []


class LocationComparisonResponse(BaseModel):
    status: str
    business_subcategory: str
    compared_scenario_count: int
    returned_result_count: int
    ranking_method: str
    best_option: Optional[LocationComparisonItem] = None
    results: List[LocationComparisonItem]
    skipped_scenarios: List[str] = []
    user_facing_note: str
