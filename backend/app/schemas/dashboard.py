from typing import Dict, List

from pydantic import BaseModel

from app.schemas.sensor_packet import SensorPacket
from app.schemas.competition import CompetitionObservationEvidence
from app.schemas.lease import LeaseCostEvidence
from app.schemas.demand import DemandEvidence
from app.schemas.recommendation import RecommendationDecision
from app.schemas.operating_profile import OperatingProfileResponse


class MonitorStatus(BaseModel):
    name: str
    value: str
    indicator: str


class MLPredictionResponse(BaseModel):
    predicted_risk_class: str
    risk_probabilities: Dict[str, float]
    predicted_monthly_net_revenue: float
    predicted_feasibility_score: float
    recommendation: str

    # Step 21: transparent post-prediction consistency guard metadata.
    risk_class_before_consistency: str | None = None
    consistency_adjusted: bool = False
    consistency_status: str | None = None
    consistency_rules_triggered: List[str] = []
    consistency_warnings: List[str] = []
    consistency_note: str | None = None
    model_version: str | None = None


class ModuleAnalysisResponse(BaseModel):
    score: float
    level: str
    summary: str
    signals: List[str]
    metrics: Dict[str, float]


class AnalysisBreakdownResponse(BaseModel):
    demand_analysis: ModuleAnalysisResponse
    competition_analysis: ModuleAnalysisResponse
    lease_cost_analysis: ModuleAnalysisResponse


class PredictionExplanationResponse(BaseModel):
    competition_score: float
    demand_score: float
    demographic_fit_score: float
    estimated_competitor_count: int
    reachable_population_estimate: float
    monthly_lease_cost_estimate: float
    monthly_operating_cost_estimate: float
    revenue_explanation: str
    risk_explanation: str
    feasibility_explanation: str
    top_positive_factors: List[str]
    top_negative_factors: List[str]


class OutputEvidenceItem(BaseModel):
    field_name: str
    label: str
    method: str
    credibility: str
    source: str
    user_note: str


class PredictionCredibilityResponse(BaseModel):
    overall_confidence_score: float
    confidence_level: str
    data_quality_score: float
    model_signal_score: float
    proxy_dependency_score: float
    observed_inputs: List[OutputEvidenceItem]
    model_predicted_outputs: List[OutputEvidenceItem]
    proxy_estimated_inputs: List[OutputEvidenceItem]
    derived_metrics: List[OutputEvidenceItem]
    user_facing_disclaimer: str
    next_data_needed: List[str]


class DashboardSummaryResponse(BaseModel):
    application_name: str
    project_phase: str

    municipality_name: str
    business_subcategory: str
    radius_km: float

    people_location_packet: SensorPacket
    competition_monitor: MonitorStatus
    revenue_monitor: MonitorStatus
    risk_monitor: MonitorStatus

    ml_prediction: MLPredictionResponse | None = None
    prediction_explanation: PredictionExplanationResponse | None = None
    analysis_breakdown: AnalysisBreakdownResponse | None = None
    prediction_credibility: PredictionCredibilityResponse | None = None
    competition_evidence: CompetitionObservationEvidence | None = None
    lease_cost_evidence: LeaseCostEvidence | None = None
    demand_evidence: DemandEvidence | None = None
    recommendation_decision: RecommendationDecision | None = None

    # Step 32B: unified operating profile returned with the dashboard so
    # frontend dashboard values and operating-profile values come from the same response.
    operating_profile: OperatingProfileResponse | None = None
