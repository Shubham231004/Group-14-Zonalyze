from __future__ import annotations

from collections import Counter
from typing import List

from app.schemas.trust_audit import TrustAuditItem, TrustAuditResponse, TrustAuditSummary


AUDIT_VERSION = "trust_audit_v1_formula_hardcoding_proxy_review"
PROJECT_PHASE = "Capstone Prototype - Trust Foundation Cleanup"


def _audit_items() -> List[TrustAuditItem]:
    """
    Static trust audit registry for current Zonalyze outputs.

    This does NOT generate predictions and does NOT remove any existing feature.
    It documents how major fields are currently produced so the team can decide
    what to keep, relabel, recalibrate, replace, or remove.
    """
    return [
        TrustAuditItem(
            field_name="population_2021",
            display_name="Population",
            current_location="scenario_feature_builder.py / processed census data",
            output_category="observed_data",
            current_method="Loaded from processed Statistics Canada 2021 census-derived CSD feature files.",
            trust_level="high",
            user_facing_risk="low",
            issue=None,
            recommended_action="Keep as observed demographic input.",
            replacement_priority="keep",
            suggested_source_or_fix="Continue citing Statistics Canada 2021 processed census source.",
        ),
        TrustAuditItem(
            field_name="household_median_total_income_2020",
            display_name="Median household income",
            current_location="scenario_feature_builder.py / processed census data",
            output_category="observed_data",
            current_method="Loaded from processed Statistics Canada 2021 census-derived CSD feature files.",
            trust_level="high",
            user_facing_risk="low",
            issue="Useful as purchasing-power context, but not a direct revenue predictor by itself.",
            recommended_action="Keep, but explain it as demographic context rather than direct business income guarantee.",
            replacement_priority="label",
            suggested_source_or_fix="Statistics Canada census income fields.",
        ),
        TrustAuditItem(
            field_name="population_density_per_km2",
            display_name="Population density",
            current_location="scenario_feature_builder.py / processed census data",
            output_category="derived_metric",
            current_method="Processed from census population and land area.",
            trust_level="high",
            user_facing_risk="low",
            issue=None,
            recommended_action="Keep as a safe derived demographic metric.",
            replacement_priority="keep",
            suggested_source_or_fix="Statistics Canada population and land area.",
        ),
        TrustAuditItem(
            field_name="reachable_population_estimate",
            display_name="Reachable population estimate",
            current_location="scenario_feature_builder.py",
            output_category="proxy_estimate",
            current_method="Calculated from municipality population multiplied by radius_population_factor().",
            trust_level="limited",
            user_facing_risk="medium",
            issue="Radius coverage factor is heuristic and does not use actual road network, catchment geometry, or neighborhood boundaries.",
            recommended_action="Relabel as Reachable Population Proxy and replace later with geospatial catchment calculation.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="Use GIS buffers, dissemination area population weighting, or travel-time catchments.",
        ),
        TrustAuditItem(
            field_name="demographic_fit_score_0_100",
            display_name="Demographic fit score",
            current_location="scenario_feature_builder.py / demographic_fit_score()",
            output_category="heuristic_formula",
            current_method="Weighted blend of youth, young adult, family, senior, diversity, and immigrant percentages using business catalog weights.",
            trust_level="weak",
            user_facing_risk="high",
            issue="Weights are catalog assumptions, not empirically calibrated from observed customer or sales data.",
            recommended_action="Rename to Demographic Fit Proxy, show limited confidence, and later calibrate using real customer or transaction datasets.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="Customer profile benchmarks, transaction data, mobility data, or survey data by business type.",
        ),
        TrustAuditItem(
            field_name="demand_score_0_100",
            display_name="Demand score",
            current_location="scenario_feature_builder.py / demand_score() and demand_data_service.py",
            output_category="heuristic_formula",
            current_method="Weighted calculation using demographic fit, market index, income, density, employment, and competition pressure.",
            trust_level="weak",
            user_facing_risk="high",
            issue="Coefficient choices are heuristic and not backed by a validated demand model.",
            recommended_action="Rename to Demand Proxy Index immediately; later replace with evidence-backed demand indicators and/or calibrated model.",
            replacement_priority="replace",
            suggested_source_or_fix="Foot traffic data, mobility data, transaction data, Google/OSM POI activity proxies, business survey data.",
        ),
        TrustAuditItem(
            field_name="foot_traffic_proxy_index",
            display_name="Foot traffic proxy index",
            current_location="demand_data_service.py",
            output_category="proxy_estimate",
            current_method="Estimated from available demographic and market signals.",
            trust_level="limited",
            user_facing_risk="medium",
            issue="Not currently based on observed pedestrian counts or mobility records.",
            recommended_action="Keep only as proxy and explicitly label it as not observed foot traffic.",
            replacement_priority="replace",
            suggested_source_or_fix="Municipal pedestrian counts, transit boarding data, mobility data, or commercial foot traffic datasets.",
        ),
        TrustAuditItem(
            field_name="competitor_count_estimate",
            display_name="Competitor count",
            current_location="competition_data_service.py / market CSV catalog / OSM service where available",
            output_category="proxy_estimate",
            current_method="Uses seeded competition observation catalog or fallback estimate; OSM POIs can supplement map evidence.",
            trust_level="limited",
            user_facing_risk="high",
            issue="Seed catalog is not complete real competitor coverage for every municipality/business combination.",
            recommended_action="Replace seeded rows with OSM/Overpass extraction and cache source metadata; show coverage gaps.",
            replacement_priority="replace",
            suggested_source_or_fix="OpenStreetMap Overpass POIs, business directories, municipal business registries.",
        ),
        TrustAuditItem(
            field_name="competition_score_0_100",
            display_name="Competition pressure index",
            current_location="competition_data_service.py / competition_service.py",
            output_category="heuristic_formula",
            current_method="Derived from competitor count, density, distance, market index, and/or catalog values.",
            trust_level="weak",
            user_facing_risk="high",
            issue="The pressure scaling is heuristic and may overstate precision.",
            recommended_action="Rename to Competition Pressure Estimate and show source components instead of implying exact score.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="Calibrate against observed market saturation, closures, or business survival data if available.",
        ),
        TrustAuditItem(
            field_name="monthly_lease_cost_estimate",
            display_name="Monthly lease cost estimate",
            current_location="lease_cost_data_service.py / scenario_feature_builder.py",
            output_category="proxy_estimate",
            current_method="Uses seeded lease evidence catalog or formula based on rent pressure/business size assumptions.",
            trust_level="limited",
            user_facing_risk="high",
            issue="Not currently sourced from verified commercial lease listings for each scenario.",
            recommended_action="Show as lease proxy/range only; prioritize user rent override and real listing integration.",
            replacement_priority="replace",
            suggested_source_or_fix="Commercial listing data, broker reports, municipal vacancy/rent data, user-provided rent quote.",
        ),
        TrustAuditItem(
            field_name="lease_cost_per_sqft_year",
            display_name="Lease cost per square foot per year",
            current_location="lease_cost_data_service.py / lease_cost_service.py",
            output_category="derived_metric",
            current_method="Derived from estimated lease and estimated square footage.",
            trust_level="medium",
            user_facing_risk="medium",
            issue="Calculation is transparent, but source lease value may be proxy-based.",
            recommended_action="Keep as derived metric, but show dependency on lease evidence credibility.",
            replacement_priority="label",
            suggested_source_or_fix="Use real lease source when available.",
        ),
        TrustAuditItem(
            field_name="monthly_operating_cost_estimate",
            display_name="Monthly operating cost estimate",
            current_location="scenario_feature_builder.py",
            output_category="heuristic_formula",
            current_method="Combines lease, staff, utilities, marketing, and fixed operating cost assumptions.",
            trust_level="weak",
            user_facing_risk="high",
            issue="Staff, utilities, marketing, and fixed cost assumptions are catalog/prototype assumptions unless user supplies values.",
            recommended_action="Expose user override fields and mark defaults as prototype assumptions.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="User inputs, industry benchmarks, Statistics Canada business cost surveys, accounting benchmarks.",
        ),
        TrustAuditItem(
            field_name="predicted_monthly_net_revenue",
            display_name="Predicted monthly net revenue",
            current_location="predictor.py / revenue_regressor.pkl",
            output_category="model_prediction",
            current_method="Random forest regressor trained on simulation-generated prototype labels.",
            trust_level="limited",
            user_facing_risk="high",
            issue="Training labels are simulation-generated, not observed business revenue outcomes.",
            recommended_action="Keep only as prototype planning estimate; add strong disclaimer and avoid claiming real forecast accuracy.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="Observed business revenue data, industry revenue benchmarks, tax/statistical business performance data where legally available.",
        ),
        TrustAuditItem(
            field_name="predicted_risk_class",
            display_name="Predicted risk class",
            current_location="predictor.py / risk_classifier.pkl / prediction_consistency_service.py",
            output_category="model_prediction",
            current_method="Random forest classifier trained on synthetic risk labels, then checked by post-prediction consistency guard.",
            trust_level="limited",
            user_facing_risk="high",
            issue="Risk labels are not observed business success/failure labels. Consistency guard reduces contradictions but does not validate the model.",
            recommended_action="Keep as Prototype Risk Estimate, show raw/adjusted status, and prioritize real outcome data later.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="Business survival/closure data, bankruptcy/registration churn, longitudinal business performance outcomes.",
        ),
        TrustAuditItem(
            field_name="predicted_feasibility_score",
            display_name="Predicted feasibility score",
            current_location="predictor.py / feasibility_regressor.pkl",
            output_category="model_prediction",
            current_method="Random forest regressor trained on simulation-generated feasibility labels.",
            trust_level="limited",
            user_facing_risk="high",
            issue="Feasibility label is synthetic and should not be presented as an objective real-world score.",
            recommended_action="Rename to Prototype Feasibility Estimate and show data limitations beside it.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="Observed outcome labels, expert-reviewed feasibility studies, lender/business survival datasets.",
        ),
        TrustAuditItem(
            field_name="recommendation_decision.final_recommendation",
            display_name="Final recommendation",
            current_location="recommendation_service.py",
            output_category="heuristic_formula",
            current_method="Rule-based combination of model predictions, credibility, competition, lease, demand, and risk probabilities.",
            trust_level="limited",
            user_facing_risk="high",
            issue="Decision thresholds and weights are heuristic and not externally validated.",
            recommended_action="Keep as decision-support label only; expose rationale, confidence, and evidence quality; avoid absolute claims.",
            replacement_priority="recalibrate",
            suggested_source_or_fix="Expert validation, observed business outcomes, sensitivity testing, and user study feedback.",
        ),
        TrustAuditItem(
            field_name="business_subcategories",
            display_name="Business subcategory catalog",
            current_location="catalogs/business_subcategories.py",
            output_category="catalog_assumption",
            current_method="Python code-based catalog of business profiles and assumptions.",
            trust_level="weak",
            user_facing_risk="medium",
            issue="Business taxonomy and assumptions are hardcoded in Python and not source-backed enough.",
            recommended_action="Move to data-backed catalog with source fields, versioning, NAICS/OSM mapping, and confidence level per row.",
            replacement_priority="replace",
            suggested_source_or_fix="CSV/PostgreSQL catalog backed by NAICS, OSM tags, and documented assumption sources.",
        ),
        TrustAuditItem(
            field_name="municipality_name",
            display_name="Municipality list",
            current_location="processed census data / catalog_service.py",
            output_category="observed_data",
            current_method="Loaded from processed census-derived municipality dataset.",
            trust_level="high",
            user_facing_risk="low",
            issue=None,
            recommended_action="Keep data-driven from census dataset.",
            replacement_priority="keep",
            suggested_source_or_fix="Processed Statistics Canada CSD dataset.",
        ),
    ]


def get_trust_audit() -> TrustAuditResponse:
    items = _audit_items()
    categories = Counter(item.output_category for item in items)

    high_risk_items = sum(1 for item in items if item.user_facing_risk == "high")
    weak_or_unacceptable_items = sum(
        1 for item in items if item.trust_level in {"weak", "unacceptable"}
    )
    items_requiring_replacement = sum(
        1 for item in items if item.replacement_priority == "replace"
    )
    items_requiring_relabeling = sum(
        1 for item in items if item.replacement_priority == "label"
    )

    summary = TrustAuditSummary(
        total_items=len(items),
        high_risk_items=high_risk_items,
        weak_or_unacceptable_items=weak_or_unacceptable_items,
        items_requiring_replacement=items_requiring_replacement,
        items_requiring_relabeling=items_requiring_relabeling,
        overall_status="cleanup_required",
        summary_message=(
            "The current prototype contains a mix of observed census inputs, derived metrics, "
            "proxy estimates, heuristic formulas, catalog assumptions, and ML outputs trained on "
            "simulation-generated labels. User-facing trust should be improved by relabeling weak "
            "metrics, replacing hardcoded assumptions, and sourcing stronger real-world evidence."
        ),
    )

    return TrustAuditResponse(
        audit_version=AUDIT_VERSION,
        project_phase=PROJECT_PHASE,
        summary=summary,
        categories=dict(categories),
        items=items,
        immediate_cleanup_order=[
            "Rename user-facing heuristic scores so they are clearly proxy/estimate labels, not factual scores.",
            "Move business_subcategories.py assumptions into a data-backed catalog with source and confidence columns.",
            "Add a scenario support/coverage validator before allowing freer user-entered inputs.",
            "Prioritize replacing competition and lease seed catalogs with source-backed OSM/listing evidence where possible.",
            "Keep ML predictions, but label them as prototype model estimates trained on simulation-generated labels until real outcome data exists.",
        ],
        implementation_notes=[
            "This audit endpoint is diagnostic only and does not remove or alter existing dashboard behavior.",
            "High-risk fields should not be hidden; they should be relabeled and explained until better data replaces them.",
            "Safe derived metrics can remain if the source inputs and formula are transparent.",
            "AI should summarize retrieved/source-backed evidence, not invent replacement values for unsupported fields.",
        ],
    )
