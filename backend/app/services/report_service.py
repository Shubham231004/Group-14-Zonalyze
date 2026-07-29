from datetime import datetime
from typing import Iterable

from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.report import FeasibilityReportResponse


def _money(value: float | int | None) -> str:
    if value is None:
        return "Not available"
    return f"${value:,.0f}"


def _pct(value: float | int | None) -> str:
    if value is None:
        return "Not available"
    return f"{value:.1f}%"


def _score(value: float | int | None) -> str:
    if value is None:
        return "Not available"
    return f"{value:.1f}/100"


def _number(value: float | int | None, decimals: int = 0) -> str:
    if value is None:
        return "Not available"
    return f"{value:,.{decimals}f}"


def _lines(items: Iterable[str]) -> str:
    values = [item for item in items if item]
    if not values:
        return "Not available"
    return "\n".join(f"- {item}" for item in values)


def _metric_lookup(dashboard: DashboardSummaryResponse, key: str) -> float | None:
    for metric in dashboard.people_location_packet.metrics:
        if metric.key == key:
            return metric.value
    return None


def build_feasibility_report(dashboard: DashboardSummaryResponse) -> FeasibilityReportResponse:
    """
    Builds a downloadable plain-text feasibility report from the same backend
    response used by the cockpit dashboard.

    The report is intentionally text-based for this phase because it is stable,
    easy to test, and does not add PDF-generation dependencies to the backend.
    """
    ml = dashboard.ml_prediction
    explanation = dashboard.prediction_explanation
    breakdown = dashboard.analysis_breakdown
    credibility = dashboard.prediction_credibility
    competition_evidence = dashboard.competition_evidence
    lease_cost_evidence = dashboard.lease_cost_evidence
    demand_evidence = dashboard.demand_evidence
    recommendation_decision = dashboard.recommendation_decision

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_city = dashboard.municipality_name.lower().replace(" ", "-")
    safe_business = dashboard.business_subcategory.lower().replace(" ", "-").replace("/", "-")
    filename = f"zonalyze-feasibility-report-{safe_city}-{safe_business}.txt"

    population_total = _metric_lookup(dashboard, "population_total")
    population_density = _metric_lookup(dashboard, "population_density_per_km2")
    median_income = _metric_lookup(dashboard, "median_total_income")
    diversity_index = _metric_lookup(dashboard, "diversity_index_0_100")
    students_pct = _metric_lookup(dashboard, "students_pct")
    families_pct = _metric_lookup(dashboard, "families_pct")
    retirees_pct = _metric_lookup(dashboard, "retirees_pct")

    report_text = f"""ZONALYZE FEASIBILITY REPORT
Generated: {generated_at}

SCENARIO
Municipality: {dashboard.municipality_name}
Business Subcategory: {dashboard.business_subcategory}
Search Radius: {dashboard.radius_km:.1f} km
Project Phase: {dashboard.project_phase}

EXECUTIVE SUMMARY
Recommendation: {recommendation_decision.recommendation_label if recommendation_decision else (ml.recommendation.replace('_', ' ').title() if ml else 'Not available')}
Decision Confidence: {_score(recommendation_decision.decision_confidence_score if recommendation_decision else None)} ({recommendation_decision.confidence_level.title() if recommendation_decision else "Not available"})
Predicted Risk Class: {ml.predicted_risk_class.title() if ml else 'Not available'}
Prototype Monthly Net Revenue Estimate: {_money(ml.predicted_monthly_net_revenue if ml else None)}
Prototype Feasibility Estimate: {_score(ml.predicted_feasibility_score if ml else None)}
Prediction Confidence: {_score(credibility.overall_confidence_score if credibility else None)} ({credibility.confidence_level.title() if credibility else "Not available"})

RECOMMENDATION DECISION
Decision Summary: {recommendation_decision.decision_summary if recommendation_decision else 'Not available'}
Decision Rationale: {recommendation_decision.decision_rationale if recommendation_decision else 'Not available'}
Action Guidance: {recommendation_decision.action_guidance if recommendation_decision else 'Not available'}
Caution Note: {recommendation_decision.caution_note if recommendation_decision else 'Not available'}

Major Strengths:
{_lines(recommendation_decision.major_strengths if recommendation_decision else [])}

Major Concerns:
{_lines(recommendation_decision.major_concerns if recommendation_decision else [])}

CORE MONITORS
Competition: {dashboard.competition_monitor.value} [{dashboard.competition_monitor.indicator.upper()}]
Revenue: {dashboard.revenue_monitor.value} [{dashboard.revenue_monitor.indicator.upper()}]
Prototype Risk Estimate: {dashboard.risk_monitor.value} [{dashboard.risk_monitor.indicator.upper()}]

DEMOGRAPHIC SNAPSHOT
Population Total: {_number(population_total)}
Population Density: {_number(population_density, 1)} people/km²
Median Income: {_money(median_income)}
Diversity Index: {_score(diversity_index)}
Youth/Student Share: {_pct(students_pct)}
Family Share: {_pct(families_pct)}
Senior/Retiree Share: {_pct(retirees_pct)}
People and Location Summary: {dashboard.people_location_packet.summary_text}

PREDICTION EXPLANATION
Revenue Explanation: {explanation.revenue_explanation if explanation else 'Not available'}
Risk Explanation: {explanation.risk_explanation if explanation else 'Not available'}
Prototype Feasibility Explanation: {explanation.feasibility_explanation if explanation else 'Not available'}

CREDIBILITY AND DATA USE
Confidence Level: {credibility.confidence_level.title() if credibility else "Not available"}
Data Quality Score: {_score(credibility.data_quality_score if credibility else None)}
Model Signal Score: {_score(credibility.model_signal_score if credibility else None)}
Proxy Dependency Score: {_score(credibility.proxy_dependency_score if credibility else None)}
Important Note: {credibility.user_facing_disclaimer if credibility else "Not available"}

COMPETITION DATA EVIDENCE
Source: {competition_evidence.source_name if competition_evidence else "No catalog row available"}
Method: {competition_evidence.method if competition_evidence else "Fallback proxy estimate"}
Credibility: {competition_evidence.credibility if competition_evidence else "limited"}
Observed Same-Category Count: {competition_evidence.observed_competitor_count if competition_evidence else "Not available"}
Competitor Density: {_number(competition_evidence.competitor_density_per_10k if competition_evidence else None, 2)} per 10,000 people
Nearest Competitor Distance: {_number(competition_evidence.nearest_competitor_distance_km if competition_evidence else None, 2)} km
Competition Pressure Index: {_score(competition_evidence.competition_pressure_index if competition_evidence else None)}
Data Quality Note: {competition_evidence.data_quality_note if competition_evidence else "Add a real POI/business listing row for this municipality and business type."}


DEMAND DATA EVIDENCE
Source: {demand_evidence.source_name if demand_evidence else "No demand evidence row available"}
Method: {demand_evidence.method if demand_evidence else "Fallback proxy estimate"}
Credibility: {demand_evidence.credibility if demand_evidence else "limited"}
Reachable Population Estimate: {_number(demand_evidence.reachable_population_estimate if demand_evidence else None)}
Target Customer Pool Estimate: {_number(demand_evidence.target_customer_pool_estimate if demand_evidence else None)}
Daytime Activity Index: {_score(demand_evidence.daytime_activity_index if demand_evidence else None)}
Foot Traffic Proxy Index: {_score(demand_evidence.foot_traffic_proxy_index if demand_evidence else None)}
Transit Access Proxy Index: {_score(demand_evidence.transit_access_proxy_index if demand_evidence else None)}
Demand Pressure Index: {_score(demand_evidence.demand_pressure_index if demand_evidence else None)}
Demand Level: {demand_evidence.demand_level.title() if demand_evidence else "Not available"}
Data Quality Note: {demand_evidence.data_quality_note if demand_evidence else "Add mobility, foot traffic, or transaction data for this scenario."}

LEASE COST DATA EVIDENCE
Source: {lease_cost_evidence.source_name if lease_cost_evidence else "No lease evidence row available"}
Method: {lease_cost_evidence.method if lease_cost_evidence else "Fallback proxy range"}
Credibility: {lease_cost_evidence.credibility if lease_cost_evidence else "limited"}
Estimated Space Requirement: {_number(lease_cost_evidence.estimated_space_sqft if lease_cost_evidence else None)} sq ft
Estimated Monthly Lease Range: {_money(lease_cost_evidence.low_monthly_lease_cost if lease_cost_evidence else None)} to {_money(lease_cost_evidence.high_monthly_lease_cost if lease_cost_evidence else None)}
Median Monthly Lease Estimate: {_money(lease_cost_evidence.median_monthly_lease_cost if lease_cost_evidence else None)}
Annual Lease Cost per Square Foot: {_money(lease_cost_evidence.lease_cost_per_sqft_year if lease_cost_evidence else None)}
Commercial Cost Pressure: {lease_cost_evidence.commercial_cost_pressure_level.title() if lease_cost_evidence else "Not available"}
Data Quality Note: {lease_cost_evidence.data_quality_note if lease_cost_evidence else "Add commercial lease listings or broker data for this scenario."}

MODEL FACTORS
Competition Pressure Estimate: {_score(explanation.competition_score if explanation else None)}
Demand Proxy Index: {_score(explanation.demand_score if explanation else None)}
Demographic Fit Score: {_score(explanation.demographic_fit_score if explanation else None)}
Estimated Competitor Count: {explanation.estimated_competitor_count if explanation else 'Not available'}
Reachable Population Estimate: {_number(explanation.reachable_population_estimate if explanation else None)}
Monthly Lease Cost Estimate: {_money(explanation.monthly_lease_cost_estimate if explanation else None)}
Monthly Operating Cost Estimate: {_money(explanation.monthly_operating_cost_estimate if explanation else None)}

POSITIVE FACTORS
{_lines(explanation.top_positive_factors if explanation else [])}

NEGATIVE FACTORS
{_lines(explanation.top_negative_factors if explanation else [])}

MODULE BREAKDOWN
Demand Analysis: {breakdown.demand_analysis.summary if breakdown else 'Not available'}
Demand Proxy Index: {_score(breakdown.demand_analysis.score if breakdown else None)}
Demand Signals:
{_lines(breakdown.demand_analysis.signals if breakdown else [])}

Competition Analysis: {breakdown.competition_analysis.summary if breakdown else 'Not available'}
Competition Pressure Estimate: {_score(breakdown.competition_analysis.score if breakdown else None)}
Competition Signals:
{_lines(breakdown.competition_analysis.signals if breakdown else [])}

Lease Cost Analysis: {breakdown.lease_cost_analysis.summary if breakdown else 'Not available'}
Lease Cost Score: {_score(breakdown.lease_cost_analysis.score if breakdown else None)}
Lease Signals:
{_lines(breakdown.lease_cost_analysis.signals if breakdown else [])}

NEXT DATA NEEDED
{_lines(credibility.next_data_needed if credibility else [])}

NOTES
This report is generated from the current Zonalyze prototype. The system separates observed census inputs, model predictions, proxy estimates, and derived metrics. Results should be treated as scenario-comparison support, not as guaranteed commercial outcomes.
"""

    return FeasibilityReportResponse(
        filename=filename,
        report_text=report_text,
    )
