from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pypdf import PdfReader

from app.schemas.scenario_history import ScenarioHistoryResponse
from app.services import scenario_history_service
from app.services.report_service import TEAM_MEMBERS, build_feasibility_report


def sample_dashboard():
    item = SimpleNamespace
    return item(
        municipality_name="Kitchener",
        business_subcategory="Coffee Shop",
        radius_km=6,
        project_phase="Capstone decision support",
        ml_prediction=item(
            recommendation="recommended",
            predicted_feasibility_score=82.4,
            predicted_monthly_net_revenue=18450,
            predicted_risk_class="medium",
        ),
        prediction_explanation=item(
            competition_score=44.0,
            demand_score=78.0,
            demographic_fit_score=83.0,
            estimated_competitor_count=12,
            monthly_operating_cost_estimate=28500,
            top_positive_factors=["Strong local demand", "Good demographic fit"],
            top_negative_factors=["Lease costs require confirmation"],
        ),
        analysis_breakdown=item(
            demand_analysis=item(summary="Demand indicators are favourable."),
            competition_analysis=item(summary="Competition is moderate."),
            lease_cost_analysis=item(summary="Lease pressure is manageable."),
        ),
        prediction_credibility=item(
            overall_confidence_score=74.0,
            confidence_level="moderate",
            data_quality_score=76.0,
            model_signal_score=72.0,
            proxy_dependency_score=35.0,
            user_facing_disclaimer="Use this result as decision support and verify costs.",
            next_data_needed=["Current broker lease quote", "Site visit"],
        ),
        competition_evidence=item(
            source_name="OpenStreetMap",
            credibility="medium",
            observed_competitor_count=12,
            competitor_density_per_10k=1.8,
            nearest_competitor_distance_km=0.7,
            competition_pressure_index=44.0,
            data_quality_note="Public listings may not be complete.",
        ),
        demand_evidence=item(
            source_name="Statistics Canada and public map evidence",
            reachable_population_estimate=92500,
            target_customer_pool_estimate=18400,
            foot_traffic_proxy_index=72.0,
            demand_pressure_index=78.0,
            demand_level="high",
            data_quality_note="Foot traffic is a proxy, not a live count.",
        ),
        lease_cost_evidence=item(
            source_name="Commercial lease proxy",
            estimated_space_sqft=1800,
            low_monthly_lease_cost=5200,
            high_monthly_lease_cost=7600,
            median_monthly_lease_cost=6400,
            lease_cost_per_sqft_year=42,
            commercial_cost_pressure_level="moderate",
            data_quality_note="Confirm with a current landlord or broker quote.",
        ),
        recommendation_decision=item(
            recommendation_label="Promising - verify the lease",
            decision_confidence_score=74.0,
            decision_summary="This location has encouraging demand and demographic alignment.",
            decision_rationale="Demand and fit outweigh moderate competition, subject to confirmed occupancy costs.",
            action_guidance="Validate the lease, visit the site, and confirm peak-period activity.",
            caution_note="This is not a guaranteed commercial outcome.",
            major_strengths=["Strong demand signal", "Good customer fit"],
            major_concerns=["Lease evidence remains estimated"],
        ),
        people_location_packet=item(
            summary_text="The selected catchment combines residential and daytime activity.",
            metrics=[
                item(key="population_total", value=256885),
                item(key="population_density_per_km2", value=1870.4),
                item(key="household_median_total_income_2020", value=92000),
                item(key="diversity_index_0_100", value=79.0),
                item(key="students_pct", value=18.2),
                item(key="families_pct", value=61.0),
                item(key="retirees_pct", value=13.1),
            ],
        ),
    )


def test_pdf_report_has_letterhead_and_team_footer():
    filename, content = build_feasibility_report(sample_dashboard())
    reader = PdfReader(BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert content.startswith(b"%PDF")
    assert filename.endswith(".pdf")
    assert len(reader.pages) >= 3
    assert "Location Feasibility Report" in text
    assert TEAM_MEMBERS in text


def test_delete_saved_scenario_removes_only_the_requested_record():
    db = MagicMock()
    record = object()
    db.query.return_value.filter.return_value.first.return_value = record
    expected = ScenarioHistoryResponse(count=0, scenarios=[])

    with patch.object(scenario_history_service, "list_saved_scenarios", return_value=expected):
        result = scenario_history_service.delete_saved_scenario(
            "scn_target", db, user_id="user_123"
        )

    db.delete.assert_called_once_with(record)
    db.commit.assert_called_once()
    assert result == expected
