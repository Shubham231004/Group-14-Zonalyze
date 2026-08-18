from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List

from app.schemas.location_comparison import (
    LocationComparisonItem,
    LocationComparisonRequest,
    LocationComparisonResponse,
)
from app.services.scenario_scoring_service import ScoredScenario, score_scenario


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

# Each scenario now does a POI-store round-trip (so the table can show real competitor
# counts), which is I/O-bound. 8 in flight keeps a 20-city comparison at roughly the
# latency of one scenario. ponytail: raise only if the DB shows it can take it.
_MAX_PARALLEL_SCENARIOS = 8


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
        # The catalog is alphabetical, so its first ten entries are tiny townships with
        # no census feature row — taking that head made every default comparison skip
        # all twenty scenarios and return an empty table. Use the named sample instead.
        candidates.extend(DEFAULT_COMPARISON_MUNICIPALITIES)

    seen = set()
    unique: List[str] = []
    for candidate in candidates:
        key = candidate.lower()
        if candidate and key not in seen:
            seen.add(key)
            unique.append(candidate)

    return unique[:20]


def _to_item(
    municipality_name: str,
    radius_km: float,
    business_subcategory: str,
    scored: ScoredScenario,
) -> LocationComparisonItem:
    """Project one scored scenario onto a comparison row.

    Every displayed number is read off the scored scenario — nothing is recomputed
    here. That is what guarantees a row matches the scenario when the user opens it.
    """
    features = scored.features
    prediction = scored.prediction
    competition = scored.competition_evidence
    demand = scored.demand_evidence
    lease = scored.lease_cost_evidence
    risk_probabilities = prediction.get("risk_probabilities") or {}

    # Prefer the evidence-backed index over the model's synthetic one, exactly as the
    # dashboard does, so the same scenario reads the same on both screens.
    competition_index = (
        competition.competition_pressure_index
        if competition is not None
        else _safe_float(features.get("competition_score_0_100"), 50.0)
    )
    demand_index = (
        demand.demand_pressure_index
        if demand is not None
        else _safe_float(features.get("demand_score_0_100"))
    )
    rent_index = (
        lease.rent_pressure_index
        if lease is not None
        else _safe_float(features.get("rent_pressure_index_0_100"), 50.0)
    )
    lease_cost = (
        lease.median_monthly_lease_cost
        if lease is not None
        else _safe_float(features.get("monthly_lease_cost_estimate"))
    )

    return LocationComparisonItem(
        rank=0,
        municipality_name=municipality_name,
        radius_km=float(radius_km),
        business_subcategory=business_subcategory,
        predicted_monthly_net_revenue=round(_safe_float(prediction.get("predicted_monthly_net_revenue")), 2),
        predicted_feasibility_score=round(_safe_float(prediction.get("predicted_feasibility_score")), 2),
        predicted_risk_class=str(prediction.get("predicted_risk_class") or "unknown"),
        recommendation=scored.decision.final_recommendation,
        high_risk_probability=round(_safe_float(risk_probabilities.get("high")), 4),
        competition_pressure_index=round(_safe_float(competition_index), 2),
        observed_competitor_count=(
            competition.observed_competitor_count if competition is not None else None
        ),
        demand_pressure_index=round(_safe_float(demand_index), 2),
        rent_pressure_index=round(_safe_float(rent_index), 2),
        reachable_population_estimate=round(_safe_float(features.get("reachable_population_estimate")), 2),
        estimated_monthly_lease_cost=round(_safe_float(lease_cost), 2),
        estimated_monthly_operating_cost=round(_safe_float(features.get("monthly_operating_cost_estimate")), 2),
        decision_score=scored.decision.decision_score,
        strengths=list(scored.decision.major_strengths[:3]),
        concerns=list(scored.decision.major_concerns[:3]),
        data_notes=[
            "Scored by the same pipeline as the main dashboard — opening any row as a "
            "scenario reproduces these exact numbers.",
            "Treat ranking as scenario-comparison support, not a guaranteed real-world outcome.",
        ],
    )


def compare_locations(request: LocationComparisonRequest) -> LocationComparisonResponse:
    candidates = _candidate_municipalities(request)
    jobs = [
        (municipality_name, radius_km)
        for municipality_name in candidates
        for radius_km in request.radius_options_km
    ]

    skipped: List[str] = []
    rows: List[LocationComparisonItem] = []

    def run(job):
        municipality_name, radius_km = job
        return job, score_scenario(
            municipality_name=municipality_name,
            business_subcategory=request.business_subcategory,
            radius_km=radius_km,
        )

    with ThreadPoolExecutor(max_workers=_MAX_PARALLEL_SCENARIOS) as pool:
        for job, future in [(job, pool.submit(run, job)) for job in jobs]:
            municipality_name, radius_km = job
            try:
                _, scored = future.result()
            except Exception as exc:
                skipped.append(f"{municipality_name} at {radius_km:g} km skipped: {type(exc).__name__}")
                continue
            rows.append(
                _to_item(municipality_name, radius_km, request.business_subcategory, scored)
            )

    rows.sort(key=lambda item: item.decision_score, reverse=True)
    limited = rows[: request.max_results]
    ranked = [item.model_copy(update={"rank": index}) for index, item in enumerate(limited, start=1)]

    return LocationComparisonResponse(
        status="success" if ranked else "no_comparable_scenarios",
        business_subcategory=request.business_subcategory,
        compared_scenario_count=len(rows),
        returned_result_count=len(ranked),
        ranking_method=(
            "Ranked by the same decision score the scenario dashboard shows: prototype revenue, "
            "feasibility, risk probability, demand, competition and rent evidence, and data credibility."
        ),
        best_option=ranked[0] if ranked else None,
        results=ranked,
        skipped_scenarios=skipped[:20],
        user_facing_note=(
            "Use this comparison to choose which municipality/radius combinations deserve deeper review. "
            "The same prototype model and evidence layers power the ranking."
        ),
    )
