from sqlalchemy.orm import Session

from app.schemas.scenario import AnalyzeScenarioRequest
from app.schemas.validation import SystemValidationResponse, ValidationCheck
from app.services.catalog_service import get_business_subcategories, get_municipalities
from app.services.dashboard_service import analyze_scenario, get_dashboard_summary
from app.services.report_service import build_feasibility_report
from app.services.competition_data_service import get_competition_observation, list_competition_observations
from app.services.lease_cost_data_service import list_lease_cost_observations
from app.services.demand_data_service import list_demand_observations


DEFAULT_MUNICIPALITY = "Kitchener"
DEFAULT_BUSINESS = "Indian Grocery Store"
DEFAULT_RADIUS_KM = 5


def _check(name: str, condition: bool, success_message: str, failure_message: str) -> ValidationCheck:
    return ValidationCheck(
        name=name,
        status="passed" if condition else "failed",
        message=success_message if condition else failure_message,
    )


def run_system_validation(db: Session) -> SystemValidationResponse:
    """
    Runs a lightweight backend validation pass for the current prototype.

    The goal is not to replace full automated testing. This endpoint gives the
    team a quick way to confirm that the main project flow still works after
    frontend/backend changes: catalog loading, dashboard response, ML outputs,
    explanations, modular analysis, scenario analysis, and report generation.
    """
    checks: list[ValidationCheck] = []

    municipalities = get_municipalities()
    business_subcategories = get_business_subcategories()

    competition_rows = list_competition_observations()
    checks.append(
        _check(
            "Competition observation catalog",
            len(competition_rows) > 0,
            f"Loaded {len(competition_rows)} competition observation rows.",
            "No competition observation rows were loaded.",
        )
    )

    lease_rows = list_lease_cost_observations()
    checks.append(
        _check(
            "Lease cost evidence catalog",
            len(lease_rows) > 0,
            f"Loaded {len(lease_rows)} lease cost evidence rows.",
            "No lease cost evidence rows were loaded.",
        )
    )

    demand_rows = list_demand_observations()
    checks.append(
        _check(
            "Demand evidence catalog",
            len(demand_rows) > 0,
            f"Loaded {len(demand_rows)} demand evidence rows.",
            "No demand evidence rows were loaded.",
        )
    )

    checks.append(
        _check(
            "Municipality catalog",
            len(municipalities) > 0,
            f"Loaded {len(municipalities)} municipality options.",
            "No municipality options were returned.",
        )
    )

    checks.append(
        _check(
            "Business subcategory catalog",
            len(business_subcategories) > 0,
            f"Loaded {len(business_subcategories)} business subcategory options.",
            "No business subcategory options were returned.",
        )
    )

    try:
        dashboard = get_dashboard_summary(db)
        checks.append(
            _check(
                "Dashboard summary endpoint",
                dashboard is not None,
                "Dashboard summary generated successfully.",
                "Dashboard summary could not be generated.",
            )
        )

        metrics = {metric.key: metric.value for metric in dashboard.people_location_packet.metrics}
        checks.append(
            _check(
                "People and location metrics",
                "population_total" in metrics and metrics.get("population_total", 0) > 0,
                "People and location packet includes population data.",
                "People and location packet is missing usable population data.",
            )
        )

        checks.append(
            _check(
                "ML prediction output",
                dashboard.ml_prediction is not None,
                "ML prediction output is present in the dashboard response.",
                "ML prediction output is missing from the dashboard response.",
            )
        )

        checks.append(
            _check(
                "Prediction explanation output",
                dashboard.prediction_explanation is not None,
                "Prediction explanation output is present.",
                "Prediction explanation output is missing.",
            )
        )

        checks.append(
            _check(
                "Modular analysis breakdown",
                dashboard.analysis_breakdown is not None,
                "Demand, competition, and lease analysis breakdown is present.",
                "Analysis breakdown is missing.",
            )
        )

        checks.append(
            _check(
                "Prediction credibility profile",
                dashboard.prediction_credibility is not None
                and dashboard.prediction_credibility.overall_confidence_score >= 0,
                "Prediction credibility profile separates observed, predicted, proxy, and derived values.",
                "Prediction credibility profile is missing.",
            )
        )

        checks.append(
            _check(
                "Competition evidence in dashboard",
                dashboard.competition_evidence is not None
                or dashboard.prediction_credibility is not None,
                "Dashboard includes competition evidence or an explicit fallback credibility profile.",
                "Dashboard is missing competition evidence and credibility context.",
            )
        )

        checks.append(
            _check(
                "Lease cost evidence in dashboard",
                dashboard.lease_cost_evidence is not None
                and dashboard.lease_cost_evidence.median_monthly_lease_cost > 0,
                "Dashboard includes lease cost evidence as a range-backed estimate.",
                "Dashboard is missing lease cost evidence.",
            )
        )

        checks.append(
            _check(
                "Demand evidence in dashboard",
                dashboard.demand_evidence is not None
                and dashboard.demand_evidence.demand_pressure_index >= 0,
                "Dashboard includes demand evidence with source method and credibility context.",
                "Dashboard is missing demand evidence.",
            )
        )

        checks.append(
            _check(
                "Recommendation decision layer",
                dashboard.recommendation_decision is not None
                and dashboard.recommendation_decision.final_recommendation in {"recommended", "borderline", "not_recommended"},
                "Dashboard includes evidence-aware recommendation decision output.",
                "Dashboard is missing the recommendation decision layer.",
            )
        )
    except Exception as exc:
        checks.append(
            ValidationCheck(
                name="Dashboard summary endpoint",
                status="failed",
                message=f"Dashboard summary raised an error: {exc}",
            )
        )
        dashboard = None

    try:
        scenario = AnalyzeScenarioRequest(
            municipality_name=DEFAULT_MUNICIPALITY,
            business_subcategory=DEFAULT_BUSINESS,
            radius_km=DEFAULT_RADIUS_KM,
        )
        scenario_dashboard = analyze_scenario(request=scenario, db=db)
        checks.append(
            _check(
                "Scenario analysis endpoint",
                scenario_dashboard.municipality_name == DEFAULT_MUNICIPALITY
                and scenario_dashboard.business_subcategory == DEFAULT_BUSINESS,
                "Scenario analysis accepts user inputs and returns matching scenario data.",
                "Scenario analysis did not return matching scenario data.",
            )
        )
    except Exception as exc:
        checks.append(
            ValidationCheck(
                name="Scenario analysis endpoint",
                status="failed",
                message=f"Scenario analysis raised an error: {exc}",
            )
        )
        scenario_dashboard = None

    try:
        source_dashboard = scenario_dashboard or dashboard
        if source_dashboard is None:
            raise ValueError("No dashboard response available for report validation.")

        report = build_feasibility_report(source_dashboard)
        checks.append(
            _check(
                "Feasibility report generation",
                bool(report.filename) and "ZONALYZE FEASIBILITY REPORT" in report.report_text,
                "Feasibility report service generated a downloadable report payload.",
                "Feasibility report payload is incomplete.",
            )
        )
    except Exception as exc:
        checks.append(
            ValidationCheck(
                name="Feasibility report generation",
                status="failed",
                message=f"Report generation raised an error: {exc}",
            )
        )

    passed_checks = sum(1 for item in checks if item.status == "passed")
    total_checks = len(checks)
    overall_status = "passed" if passed_checks == total_checks else "failed"

    return SystemValidationResponse(
        overall_status=overall_status,
        passed_checks=passed_checks,
        total_checks=total_checks,
        checks=checks,
    )
