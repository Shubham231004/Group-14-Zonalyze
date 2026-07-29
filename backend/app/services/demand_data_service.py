from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from app.schemas.demand import DemandEvidence


DEMAND_OBSERVATIONS_PATH = Path("app/data/market/demand_observations_seed.csv")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "" or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(value: str) -> str:
    return str(value or "").strip().lower()


def _demand_level(index: float) -> str:
    if index >= 75:
        return "strong"
    if index >= 50:
        return "moderate"
    return "weak"


def _row_to_evidence(row: pd.Series, features: Dict[str, Any] | None = None) -> DemandEvidence:
    features = features or {}
    reachable = _safe_float(features.get("reachable_population_estimate"), 0.0)
    demographic_fit = _safe_float(features.get("demographic_fit_score_0_100"), 0.0)
    target_factor = _safe_float(row.get("target_customer_pool_factor"), 0.035)
    target_pool = max(0.0, reachable * target_factor)
    demand_index = _safe_float(row.get("demand_pressure_index"), _safe_float(features.get("demand_score_0_100"), 50.0))

    return DemandEvidence(
        municipality_name=str(row.get("municipality_name", "")),
        business_subcategory=str(row.get("business_subcategory", "")),
        source_name=str(row.get("source_name", "Zonalyze demand evidence catalog")),
        source_method=str(row.get("source_method", "Catalog-backed demand proxy")),
        source_date=str(row.get("source_date", "unknown")),
        method=str(row.get("method", "catalog_seed_proxy")),
        credibility=str(row.get("credibility", "medium")),
        reachable_population_estimate=round(reachable, 2),
        target_customer_pool_estimate=round(target_pool, 2),
        daytime_activity_index=_safe_float(row.get("daytime_activity_index"), 50.0),
        foot_traffic_proxy_index=_safe_float(row.get("foot_traffic_proxy_index"), 50.0),
        transit_access_proxy_index=_safe_float(row.get("transit_access_proxy_index"), 50.0),
        demographic_fit_score=round(demographic_fit, 2),
        demand_pressure_index=round(demand_index, 2),
        demand_level=_demand_level(demand_index),
        data_quality_note=str(row.get("data_quality_note", "Seeded demand proxy. Replace with real mobility, transaction, or foot-traffic data when available.")),
    )


def _fallback_from_features(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
    features: Dict[str, Any],
) -> DemandEvidence:
    reachable = _safe_float(features.get("reachable_population_estimate"), 0.0)
    demo_fit = _safe_float(features.get("demographic_fit_score_0_100"), 50.0)
    density = _safe_float(features.get("population_density_per_km2"), 0.0)
    income_index = _safe_float(features.get("income_index_0_100"), _safe_float(features.get("market_base_index_0_100"), 50.0))
    existing_demand = _safe_float(features.get("demand_score_0_100"), 50.0)

    density_signal = min(100.0, density / 25.0)
    radius_signal = 62.0 if radius_km >= 5 else 54.0
    demand_index = max(0.0, min(100.0, existing_demand * 0.45 + demo_fit * 0.25 + density_signal * 0.15 + income_index * 0.10 + radius_signal * 0.05))

    foot_traffic = max(20.0, min(90.0, density_signal * 0.55 + demand_index * 0.45))
    daytime_activity = max(20.0, min(90.0, demand_index * 0.70 + density_signal * 0.30))
    transit_access = max(20.0, min(90.0, density_signal * 0.60 + 25.0))
    target_pool = reachable * 0.035

    return DemandEvidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        source_name="Zonalyze feature fallback",
        source_method="Fallback demand estimate generated from reachable population, demographic fit, density, and market signals",
        source_date="runtime",
        method="feature_fallback_proxy",
        credibility="limited",
        reachable_population_estimate=round(reachable, 2),
        target_customer_pool_estimate=round(target_pool, 2),
        daytime_activity_index=round(daytime_activity, 2),
        foot_traffic_proxy_index=round(foot_traffic, 2),
        transit_access_proxy_index=round(transit_access, 2),
        demographic_fit_score=round(demo_fit, 2),
        demand_pressure_index=round(demand_index, 2),
        demand_level=_demand_level(demand_index),
        data_quality_note="No demand evidence row exists for this scenario yet. This is an explicit proxy and should be replaced with mobility, transaction, or foot-traffic data.",
    )


def _index_from_count(count: int, base: float, per_unit: float) -> float:
    """Transparent count -> 0..100 index (saturating). The honest signal is the
    raw count (stated in the note); the index is just a convenience scale."""
    return round(min(100.0, base + count * per_unit), 2)


def _ground_demand_from_store(
    evidence: DemandEvidence, center_lat: float, center_lon: float, radius_km: float
) -> DemandEvidence:
    """Replace the proxy transit/foot-traffic indices with values derived from the
    real owned POI store (transit stops + commercial POIs in the radius). Only the
    local store is used — never live Overpass — so this is fast and offline-safe.
    Returns the evidence unchanged if the store isn't imported yet."""
    from app.services.osm_service import COMMERCIAL_ACTIVITY_TAGS, TRANSIT_TAGS
    from app.services.poi_query_service import fetch_pois_from_db

    transit = fetch_pois_from_db(TRANSIT_TAGS, center_lat, center_lon, radius_km, 300)
    commercial = fetch_pois_from_db(COMMERCIAL_ACTIVITY_TAGS, center_lat, center_lon, radius_km, 300)
    if transit is None or commercial is None:
        return evidence  # store not available -> keep the feature-derived proxy

    transit_count, commercial_count = len(transit), len(commercial)
    transit_index = _index_from_count(transit_count, 15.0, 2.5)
    foot_traffic = _index_from_count(commercial_count, 20.0, 3.0)
    return evidence.model_copy(
        update={
            "transit_access_proxy_index": transit_index,
            "foot_traffic_proxy_index": foot_traffic,
            "daytime_activity_index": round(min(100.0, foot_traffic * 0.6 + transit_index * 0.4), 2),
            "method": evidence.method if "osm_grounded" in evidence.method else f"{evidence.method}+osm_grounded",
            "credibility": "medium-high",
            "data_quality_note": (
                f"Transit access and foot-traffic are derived from real OpenStreetMap coverage in the "
                f"Zonalyze POI store: {transit_count} transit stops and {commercial_count} commercial POIs "
                f"within {radius_km:g} km of the analysed point."
            ),
        }
    )


def load_demand_observations() -> pd.DataFrame:
    if not DEMAND_OBSERVATIONS_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(DEMAND_OBSERVATIONS_PATH)


def list_demand_observations() -> List[DemandEvidence]:
    df = load_demand_observations()
    if df.empty:
        return []
    return [_row_to_evidence(row) for _, row in df.iterrows()]


def get_demand_evidence(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
    features: Dict[str, Any],
    center_lat: float | None = None,
    center_lon: float | None = None,
) -> DemandEvidence:
    evidence = _resolve_demand_evidence(municipality_name, business_subcategory, radius_km, features)
    if center_lat is not None and center_lon is not None:
        evidence = _ground_demand_from_store(evidence, center_lat, center_lon, radius_km)
    return evidence


def _resolve_demand_evidence(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
    features: Dict[str, Any],
) -> DemandEvidence:
    df = load_demand_observations()
    if not df.empty:
        exact = df[
            (df["municipality_name"].map(_normalize) == _normalize(municipality_name))
            & (df["business_subcategory"].map(_normalize) == _normalize(business_subcategory))
        ]
        if not exact.empty:
            return _row_to_evidence(exact.iloc[0], features)

        municipality_only = df[df["municipality_name"].map(_normalize) == _normalize(municipality_name)]
        if not municipality_only.empty:
            row = municipality_only.iloc[0].copy()
            row["business_subcategory"] = business_subcategory
            row["source_method"] = (
                "Municipality-level demand proxy. Exact business subcategory row was not available, "
                "so a local demand evidence row was reused as a fallback."
            )
            row["method"] = "municipality_catalog_proxy"
            row["credibility"] = "limited-medium"
            row["data_quality_note"] = "Municipality has demand evidence, but this exact business subcategory does not."
            return _row_to_evidence(row, features)

    return _fallback_from_features(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
        features=features,
    )


def apply_demand_evidence_to_features(
    features: Dict[str, Any],
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
) -> Dict[str, Any]:
    evidence = get_demand_evidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
        features=features,
    )

    updated = dict(features)
    updated["demand_score_0_100"] = evidence.demand_pressure_index
    updated["target_customer_pool_estimate"] = evidence.target_customer_pool_estimate
    updated["daytime_activity_index"] = evidence.daytime_activity_index
    updated["foot_traffic_proxy_index"] = evidence.foot_traffic_proxy_index
    updated["transit_access_proxy_index"] = evidence.transit_access_proxy_index
    updated["demand_data_source"] = evidence.source_name
    updated["demand_data_method"] = evidence.method
    updated["demand_data_credibility"] = evidence.credibility
    updated["demand_level"] = evidence.demand_level
    return updated


def _demo() -> None:
    # ponytail check: the count->index mapping and saturation must hold.
    assert _index_from_count(0, 15.0, 2.5) == 15.0
    assert _index_from_count(10, 15.0, 2.5) == 40.0
    assert _index_from_count(100, 15.0, 2.5) == 100.0  # saturates at 100
    print("demand_data_service demo OK")


if __name__ == "__main__":
    _demo()
