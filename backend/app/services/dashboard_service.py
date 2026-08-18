from sqlalchemy.orm import Session

from app.schemas.dashboard import (
    AnalysisBreakdownResponse,
    DashboardSummaryResponse,
    MLPredictionResponse,
    MonitorStatus,
)
from app.schemas.scenario import AnalyzeScenarioRequest
from app.services.competition_service import analyze_competition
from app.services.demand_service import analyze_demand
from app.services.explanation_service import build_prediction_explanation
from app.services.lease_cost_service import analyze_lease_cost
from app.services.people_location_service import get_people_location_packet
from app.services.scenario_scoring_service import score_scenario


DEFAULT_MUNICIPALITY = "Kitchener"
DEFAULT_BUSINESS_SUBCATEGORY = "Indian Grocery Store"
DEFAULT_RADIUS_KM = 5


def get_dashboard_summary(db: Session) -> DashboardSummaryResponse:
    """
    Returns the default ML-backed dashboard state.

    This keeps the GET /dashboard-summary endpoint aligned with the newer
    municipality_name / business_subcategory request schema.
    """
    default_request = AnalyzeScenarioRequest(
        municipality_name=DEFAULT_MUNICIPALITY,
        business_subcategory=DEFAULT_BUSINESS_SUBCATEGORY,
        radius_km=DEFAULT_RADIUS_KM,
    )
    return analyze_scenario(request=default_request, db=db)


def analyze_scenario(request: AnalyzeScenarioRequest, db: Session) -> DashboardSummaryResponse:
    # Features, prediction, evidence and the recommendation all come from the shared
    # scenario core, so this dashboard and the location-comparison table can never
    # disagree about the same scenario. Everything below is presentation only.
    scored = score_scenario(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )
    features = scored.features
    prediction_result = scored.prediction
    prediction_credibility = scored.credibility
    competition_evidence = scored.competition_evidence
    lease_cost_evidence = scored.lease_cost_evidence
    demand_evidence = scored.demand_evidence
    recommendation_decision = scored.decision

    explanation = build_prediction_explanation(
        features=features,
        prediction_result=prediction_result,
    )

    analysis_breakdown = AnalysisBreakdownResponse(
        demand_analysis=analyze_demand(features),
        competition_analysis=analyze_competition(features),
        lease_cost_analysis=analyze_lease_cost(
            features=features,
            prediction_result=prediction_result,
        ),
    )

    people_packet = get_people_location_packet(
        request=request,
        db=db,
    )

    predicted_revenue = prediction_result["predicted_monthly_net_revenue"]
    predicted_risk = prediction_result["predicted_risk_class"]
    competition_score = features["competition_score_0_100"]

    if competition_score < 35:
        competition_indicator = "green"
    elif competition_score < 65:
        competition_indicator = "yellow"
    else:
        competition_indicator = "red"

    if predicted_revenue > 0:
        revenue_indicator = "green"
    elif predicted_revenue > -10000:
        revenue_indicator = "yellow"
    else:
        revenue_indicator = "red"

    if predicted_risk == "low":
        risk_indicator = "green"
    elif predicted_risk == "medium":
        risk_indicator = "yellow"
    else:
        risk_indicator = "red"

    return DashboardSummaryResponse(
        application_name="Zonalyze",
        project_phase="Capstone Prototype - Trust-Aware Evidence Layer",
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        people_location_packet=people_packet,
        competition_monitor=MonitorStatus(
            name="Competition Pressure Estimate",
            value=f"{competition_score:.1f}/100 estimated competition pressure",
            indicator=competition_indicator,
        ),
        revenue_monitor=MonitorStatus(
            name="Prototype Revenue Estimate",
            value=f"${predicted_revenue:,.0f} prototype monthly net revenue estimate",
            indicator=revenue_indicator,
        ),
        risk_monitor=MonitorStatus(
            name="Prototype Risk Estimate",
            value=f"{predicted_risk.title()} prototype risk estimate",
            indicator=risk_indicator,
        ),
        ml_prediction=MLPredictionResponse(**prediction_result),
        prediction_explanation=explanation,
        analysis_breakdown=analysis_breakdown,
        prediction_credibility=prediction_credibility,
        competition_evidence=competition_evidence,
        lease_cost_evidence=lease_cost_evidence,
        demand_evidence=demand_evidence,
        recommendation_decision=recommendation_decision,
    )
