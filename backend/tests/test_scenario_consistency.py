"""The comparison table and the scenario dashboard must never disagree.

They used to: the dashboard applied the evidence-aware recommendation layer while the
comparison ranked on the raw model recommendation plus a second, private 0-100 formula.
The same city read "borderline / 60.1" in the table and "recommended / 90.7" when opened
as a scenario. Both now go through score_scenario; this test is what keeps them there.

Skipped when the trained model artifacts are absent (they are git-ignored), matching the
dependency-light policy in conftest.
"""
from __future__ import annotations

import pytest

from app.ml.predictor import models_available

pytestmark = pytest.mark.skipif(
    not models_available()[0],
    reason="trained model artifacts not present; see DEPLOYMENT.md",
)

BUSINESS = "Indian Grocery Store"
CITIES = ["Waterloo", "London", "Cambridge"]
RADIUS = 5.0


def test_comparison_row_matches_the_scenario_it_links_to():
    from app.schemas.location_comparison import LocationComparisonRequest
    from app.services.location_comparison_service import compare_locations
    from app.services.scenario_scoring_service import score_scenario

    comparison = compare_locations(
        LocationComparisonRequest(
            business_subcategory=BUSINESS,
            candidate_municipalities=CITIES,
            radius_options_km=[RADIUS],
        )
    )
    assert comparison.results, "no rows scored; the comparison endpoint is broken"

    for row in comparison.results:
        scored = score_scenario(
            municipality_name=row.municipality_name,
            business_subcategory=BUSINESS,
            radius_km=RADIUS,
        )
        where = f"{row.municipality_name} @ {RADIUS:g}km"
        assert row.decision_score == scored.decision.decision_score, f"decision score drifted: {where}"
        assert row.recommendation == scored.decision.final_recommendation, f"recommendation drifted: {where}"
        assert row.predicted_feasibility_score == round(
            scored.prediction["predicted_feasibility_score"], 2
        ), f"feasibility drifted: {where}"
        assert row.predicted_risk_class == scored.prediction["predicted_risk_class"], f"risk drifted: {where}"


def test_competitor_count_is_explained_not_bare():
    """A count nobody can account for is a count nobody trusts: whenever the POI store
    answers, the evidence must state how many businesses were scanned to reach it."""
    from app.services.scenario_scoring_service import score_scenario

    scored = score_scenario(
        municipality_name="Waterloo",
        business_subcategory=BUSINESS,
        radius_km=RADIUS,
    )
    evidence = scored.competition_evidence
    assert evidence is not None
    if evidence.method == "live_osm_competitor_scan":
        assert "Scanned" in evidence.data_quality_note
        assert str(evidence.observed_competitor_count) in evidence.data_quality_note


def test_a_named_indian_grocer_on_a_broad_tag_counts_as_a_competitor():
    """Regression: "Desi Point" (shop=convenience, name matches the "desi" alias) scored
    50 against a 55 threshold and was dropped from an Indian-grocery scan."""
    from app.services.osm_service import _is_relevant_competitor

    item = {
        "name": "Desi Point",
        "tags": {"name": "Desi Point", "shop": "convenience"},
    }
    assert _is_relevant_competitor(item, BUSINESS), item.get("relevance_reasons")

    # A plain convenience store with no business-specific name evidence still must not.
    unrelated = {"name": "Circle K", "tags": {"name": "Circle K", "shop": "convenience"}}
    assert not _is_relevant_competitor(unrelated, BUSINESS)


def test_ambiguous_municipality_resolves_to_the_larger_place():
    """Ontario has two CSDs named "Hamilton"; requests carry only the name."""
    from app.ml.scenario_feature_builder import get_city_row

    assert float(get_city_row("Hamilton")["population_2021"]) > 100_000
