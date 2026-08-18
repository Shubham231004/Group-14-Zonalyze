"""The single place that turns (municipality, business, radius) into a scored scenario.

The dashboard and the location comparison each used to assemble this themselves, and
they drifted apart: the dashboard applied the evidence-aware recommendation layer
(`build_recommendation_decision`) while the comparison ranked on the RAW model
recommendation plus a second, private 0-100 formula of its own. Same city, same
business, same radius could therefore read "borderline / 60.1" in the comparison table
and "recommended / 71.4" the moment it was opened as a scenario, which is exactly the
kind of contradiction that destroys trust in the tool.

Both callers now go through `score_scenario`, so there is one decision score and one
recommendation per scenario, by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.ml.predictor import get_predictor
from app.ml.scenario_feature_builder import build_prediction_features
from app.schemas.competition import CompetitionObservationEvidence
from app.schemas.dashboard import PredictionCredibilityResponse
from app.schemas.demand import DemandEvidence
from app.schemas.lease import LeaseCostEvidence
from app.schemas.recommendation import RecommendationDecision
from app.services.competition_data_service import (
    build_osm_competition_evidence,
    get_competition_observation,
)
from app.services.credibility_service import build_prediction_credibility
from app.services.demand_data_service import get_demand_evidence
from app.services.lease_cost_data_service import get_lease_cost_evidence
from app.services.osm_service import fetch_osm_competitors
from app.services.prediction_consistency_service import apply_prediction_consistency_guard
from app.services.recommendation_service import build_recommendation_decision


@dataclass
class ScoredScenario:
    features: Dict[str, Any]
    prediction: Dict[str, Any]
    credibility: PredictionCredibilityResponse
    competition_evidence: Optional[CompetitionObservationEvidence]
    lease_cost_evidence: Optional[LeaseCostEvidence]
    demand_evidence: Optional[DemandEvidence]
    decision: RecommendationDecision
    center_lat: float
    center_lon: float


def score_scenario(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
) -> ScoredScenario:
    """Build features, predict, gather evidence, and decide — in that order.

    Raises ValueError for an unknown municipality or business subcategory (handled
    centrally in app.main as a 400).
    """
    # The model is scored on the clean, training-consistent feature vector. Evidence
    # services below are read-only: they produce display/decision objects and must NOT
    # mutate the feature vector, whose scale the model was trained on.
    features = build_prediction_features(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
    )
    features["municipality_name"] = municipality_name

    # Imported here (not at module scope) to avoid a circular import: geospatial_service
    # imports the evidence services this module also uses.
    from app.services.geospatial_service import _center_for_municipality

    center_lat, center_lon = _center_for_municipality(municipality_name)
    population = float(features.get("population_2021", 0) or 0)

    # Real competition from the owned POI store; falls back to the seed observation when
    # the store isn't reachable (build_osm_competition_evidence returns None).
    # limit=2000: this drives the "Nearby Competition" count, which must reflect
    # everything in radius, not just what the map renders.
    osm_competitors = fetch_osm_competitors(
        business_subcategory, center_lat, center_lon, radius_km,
        limit=2000, store_only=True,
    )
    competition_evidence = build_osm_competition_evidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        population=population,
        osm_elements=osm_competitors.elements,
        is_live=osm_competitors.status == "live_osm",
        scan_note=osm_competitors.note,
    ) or get_competition_observation(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
        population=population,
    )

    lease_cost_evidence = get_lease_cost_evidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
        features=features,
    )
    demand_evidence = get_demand_evidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
        features=features,
        center_lat=center_lat,
        center_lon=center_lon,
    )

    prediction = apply_prediction_consistency_guard(
        prediction_result=get_predictor().predict(features),
        features=features,
    )
    credibility = build_prediction_credibility(
        features=features,
        prediction_result=prediction,
    )
    decision = build_recommendation_decision(
        features=features,
        prediction_result=prediction,
        credibility=credibility,
        competition_evidence=competition_evidence,
        lease_cost_evidence=lease_cost_evidence,
        demand_evidence=demand_evidence,
    )

    # The legacy ml_prediction.recommendation field is the same label the decision layer
    # produced. Keeping them in sync here (rather than in each caller) is what stops the
    # comparison table and the dashboard from disagreeing.
    prediction = {**prediction, "recommendation": decision.final_recommendation}

    return ScoredScenario(
        features=features,
        prediction=prediction,
        credibility=credibility,
        competition_evidence=competition_evidence,
        lease_cost_evidence=lease_cost_evidence,
        demand_evidence=demand_evidence,
        decision=decision,
        center_lat=center_lat,
        center_lon=center_lon,
    )
