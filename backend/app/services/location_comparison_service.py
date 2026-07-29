from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

from app.ml.predictor import get_predictor
from app.ml.scenario_feature_builder import build_prediction_features
from app.schemas.location_comparison import (
    LocationComparisonItem,
    LocationComparisonRequest,
    LocationComparisonResponse,
)
from app.services.catalog_service import get_municipalities
from app.services.prediction_consistency_service import apply_prediction_consistency_guard


DEFAULT_COMPARISON_MUNICIPALITIES = [
    "Kitchener",
    "Waterloo",
    "Cambridge",
    "Guelph",
    "London",
    "Kingston",
    "Hamilton",
    "Ottawa",
    "Toronto",
    "Mississauga",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        return number if math.isfinite(number) else default
    except Exception:
        return default


def _clean_name(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _candidate_municipalities(request: LocationComparisonRequest) -> List[str]:
    candidates: List[str] = []

    if request.base_municipality_name:
        candidates.append(_clean_name(request.base_municipality_name))

    candidates.extend(_clean_name(item) for item in request.candidate_municipalities)

    if not candidates:
        # Use catalog values if available, but keep it bounded so this endpoint stays fast.
        try:
            catalog = get_municipalities()
            candidates.extend([_clean_name(item) for item in catalog[:10]])
        except Exception:
            candidates.extend(DEFAULT_COMPARISON_MUNICIPALITIES)

    seen = set()
    unique: List[str] = []
    for candidate in candidates:
        key = candidate.lower()
        if candidate and key not in seen:
            seen.add(key)
            unique.append(candidate)

    return unique[:20]


def _risk_penalty(predicted_risk_class: str) -> float:
    risk = str(predicted_risk_class or "").lower()
    if risk == "low":
        return 0.0
    if risk == "medium":
        return 12.0
    return 28.0


def _recommendation_bonus(recommendation: str) -> float:
    rec = str(recommendation or "").lower()
    if rec in {"recommended", "strong_recommend", "strongly_recommended"}:
        return 8.0
    if rec in {"borderline", "review", "needs_review"}:
        return 0.0
    return -8.0


def _decision_score(features: Dict[str, Any], prediction: Dict[str, Any]) -> float:
    feasibility = _safe_float(prediction.get("predicted_feasibility_score"), 0.0)
    revenue = _safe_float(prediction.get("predicted_monthly_net_revenue"), 0.0)
    demand = _safe_float(features.get("demand_pressure_index") or features.get("demand_score_0_100"), 0.0)
    competition = _safe_float(features.get("competition_pressure_index") or features.get("competition_score_0_100"), 50.0)
    rent = _safe_float(features.get("rent_pressure_index") or features.get("rent_pressure_index_0_100"), 50.0)
    high_risk_probability = _safe_float((prediction.get("risk_probabilities") or {}).get("high"), 0.0) * 100

    # This ranking is an explicit comparison score, not a trained model output.
    # It normalizes the already-produced model/evidence signals so business owners can compare options.
    revenue_component = max(-20.0, min(20.0, revenue / 2500.0))
    score = (
        feasibility * 0.42
        + demand * 0.18
        + (100.0 - competition) * 0.13
        + (100.0 - rent) * 0.10
        + revenue_component
        - high_risk_probability * 0.10
        - _risk_penalty(str(prediction.get("predicted_risk_class")))
        + _recommendation_bonus(str(prediction.get("recommendation")))
    )
    # Floor at -100, not 0: weak scenarios (high risk, negative revenue) all used
    # to flatten to 0.0, which erased the relative ranking. A negative score is
    # honest — it means "below viability" — and options still rank against each other.
    return round(max(-100.0, min(100.0, score)), 2)


def _strengths_and_concerns(features: Dict[str, Any], prediction: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    strengths: List[str] = []
    concerns: List[str] = []

    demand = _safe_float(features.get("demand_pressure_index") or features.get("demand_score_0_100"), 0.0)
    competition = _safe_float(features.get("competition_pressure_index") or features.get("competition_score_0_100"), 0.0)
    rent = _safe_float(features.get("rent_pressure_index") or features.get("rent_pressure_index_0_100"), 0.0)
    revenue = _safe_float(prediction.get("predicted_monthly_net_revenue"), 0.0)
    feasibility = _safe_float(prediction.get("predicted_feasibility_score"), 0.0)

    if demand >= 60:
        strengths.append(f"Demand signal is stronger at {demand:.1f}/100.")
    elif demand < 40:
        concerns.append(f"Demand signal is weak at {demand:.1f}/100.")

    if competition <= 40:
        strengths.append(f"Competition pressure is manageable at {competition:.1f}/100.")
    elif competition >= 70:
        concerns.append(f"Competition pressure is high at {competition:.1f}/100.")

    if rent <= 45:
        strengths.append(f"Rent pressure is relatively manageable at {rent:.1f}/100.")
    elif rent >= 70:
        concerns.append(f"Rent pressure is high at {rent:.1f}/100.")

    if revenue > 0:
        strengths.append(f"Predicted monthly net revenue is positive at ${revenue:,.0f}.")
    else:
        concerns.append(f"Predicted monthly net revenue is negative at ${revenue:,.0f}.")

    if feasibility >= 60:
        strengths.append(f"Feasibility score is comparatively strong at {feasibility:.1f}/100.")
    elif feasibility < 35:
        concerns.append(f"Feasibility score is weak at {feasibility:.1f}/100.")

    return strengths[:3], concerns[:3]


def compare_locations(request: LocationComparisonRequest) -> LocationComparisonResponse:
    predictor = get_predictor()
    candidates = _candidate_municipalities(request)
    skipped: List[str] = []
    rows: List[LocationComparisonItem] = []

    for municipality_name in candidates:
        for radius_km in request.radius_options_km:
            try:
                features = build_prediction_features(
                    municipality_name=municipality_name,
                    business_subcategory=request.business_subcategory,
                    radius_km=radius_km,
                )
                features["municipality_name"] = municipality_name
                # Predict on the clean, training-consistent feature row; evidence
                # is not applied to model inputs here.
                raw_prediction = predictor.predict(features)
                prediction = apply_prediction_consistency_guard(
                    prediction_result=raw_prediction, features=features
                )

                strengths, concerns = _strengths_and_concerns(features, prediction)
                score = _decision_score(features, prediction)
                risk_probabilities = prediction.get("risk_probabilities") or {}

                rows.append(
                    LocationComparisonItem(
                        rank=0,
                        municipality_name=municipality_name,
                        radius_km=float(radius_km),
                        business_subcategory=request.business_subcategory,
                        predicted_monthly_net_revenue=round(_safe_float(prediction.get("predicted_monthly_net_revenue")), 2),
                        predicted_feasibility_score=round(_safe_float(prediction.get("predicted_feasibility_score")), 2),
                        predicted_risk_class=str(prediction.get("predicted_risk_class") or "unknown"),
                        recommendation=str(prediction.get("recommendation") or "review"),
                        high_risk_probability=round(_safe_float(risk_probabilities.get("high")), 4),
                        competition_pressure_index=round(_safe_float(features.get("competition_pressure_index") or features.get("competition_score_0_100")), 2),
                        demand_pressure_index=round(_safe_float(features.get("demand_pressure_index") or features.get("demand_score_0_100")), 2),
                        rent_pressure_index=round(_safe_float(features.get("rent_pressure_index") or features.get("rent_pressure_index_0_100")), 2),
                        reachable_population_estimate=round(_safe_float(features.get("reachable_population_estimate")), 2),
                        estimated_monthly_lease_cost=round(_safe_float(features.get("monthly_lease_cost_estimate")), 2),
                        estimated_monthly_operating_cost=round(_safe_float(features.get("monthly_operating_cost_estimate")), 2),
                        decision_score=score,
                        strengths=strengths,
                        concerns=concerns,
                        data_notes=[
                            "Comparison uses the same ML/evidence pipeline as the main dashboard.",
                            "Treat ranking as scenario-comparison support, not a guaranteed real-world outcome.",
                        ],
                    )
                )
            except Exception as exc:
                skipped.append(f"{municipality_name} at {radius_km:g} km skipped: {type(exc).__name__}")
                continue

    rows.sort(key=lambda item: item.decision_score, reverse=True)
    limited = rows[: request.max_results]
    ranked = [item.model_copy(update={"rank": index}) for index, item in enumerate(limited, start=1)]

    return LocationComparisonResponse(
        status="success" if ranked else "no_comparable_scenarios",
        business_subcategory=request.business_subcategory,
        compared_scenario_count=len(rows),
        returned_result_count=len(ranked),
        ranking_method=(
            "Decision score combines feasibility, predicted revenue, risk probability, demand pressure, "
            "competition pressure, rent pressure, and recommendation status."
        ),
        best_option=ranked[0] if ranked else None,
        results=ranked,
        skipped_scenarios=skipped[:20],
        user_facing_note=(
            "Use this comparison to choose which municipality/radius combinations deserve deeper review. "
            "The same prototype model and evidence layers power the ranking."
        ),
    )
