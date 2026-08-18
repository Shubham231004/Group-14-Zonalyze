from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.schemas.competition import CompetitionObservationEvidence

COMPETITION_OBSERVATIONS_PATH = Path(
    "app/data/market/competition_observations_seed.csv"
)

RADIUS_COLUMNS = {
    1: "observed_count_1km",
    3: "observed_count_3km",
    5: "observed_count_5km",
    10: "observed_count_10km",
    25: "observed_count_25km",
}


def _clean(value: Any) -> str:
    return str(value or "").strip().lower()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    return int(round(_safe_float(value, float(default))))


def _load_observations() -> pd.DataFrame:
    if not COMPETITION_OBSERVATIONS_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(COMPETITION_OBSERVATIONS_PATH)


def _radius_column(radius_km: float) -> str:
    available = sorted(RADIUS_COLUMNS)
    selected = min(available, key=lambda value: abs(value - radius_km))
    return RADIUS_COLUMNS[selected]


def _competition_pressure_index(
    observed_count: int,
    competitor_density_per_10k: float,
    nearest_distance_km: float | None,
) -> float:
    """
    This is a derived index, not a real-world label.

    The important change is that it is derived from a competition observation
    catalog instead of being created only from demographic formulas. When the
    catalog is replaced by OSM/Google/municipal business data, the same index
    will be grounded in stronger market observations.
    """
    count_component = min(100.0, observed_count * 3.2)
    density_component = min(100.0, competitor_density_per_10k * 9.0)

    if nearest_distance_km is None or nearest_distance_km <= 0:
        proximity_component = 45.0
    else:
        proximity_component = max(0.0, min(100.0, 100.0 - nearest_distance_km * 32.0))

    score = count_component * 0.42 + density_component * 0.38 + proximity_component * 0.20
    return round(max(0.0, min(100.0, score)), 2)


def get_competition_observation(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
    population: float,
) -> CompetitionObservationEvidence | None:
    df = _load_observations()
    if df.empty:
        return None

    match = df[
        (df["municipality_name"].map(_clean) == _clean(municipality_name))
        & (df["business_subcategory"].map(_clean) == _clean(business_subcategory))
    ]

    if match.empty:
        return None

    row = match.iloc[0]
    count_col = _radius_column(radius_km)
    observed_count = _safe_int(row.get(count_col), 0)
    density_per_10k = observed_count / max(1.0, population / 10000.0)
    nearest = _safe_float(row.get("nearest_competitor_distance_km"), 0.0)
    pressure = _competition_pressure_index(observed_count, density_per_10k, nearest)

    return CompetitionObservationEvidence(
        municipality_name=str(row.get("municipality_name")),
        business_subcategory=str(row.get("business_subcategory")),
        source_name=str(row.get("source_name")),
        source_method=str(row.get("source_method")),
        source_date=str(row.get("source_date")),
        method="data_catalog_observation_with_derived_pressure_index",
        credibility="medium" if observed_count > 0 else "limited",
        observed_competitor_count=observed_count,
        competitor_density_per_10k=round(density_per_10k, 3),
        nearest_competitor_distance_km=round(nearest, 2) if nearest else None,
        avg_competitor_rating=round(_safe_float(row.get("avg_competitor_rating")), 2),
        chain_share_pct=round(_safe_float(row.get("chain_share_pct")), 2),
        competition_pressure_index=pressure,
        data_quality_note=str(row.get("data_quality_note")),
    )


def build_osm_competition_evidence(
    municipality_name: str,
    business_subcategory: str,
    population: float,
    osm_elements: List[Dict[str, Any]],
    is_live: bool,
    scan_note: str = "",
) -> Optional[CompetitionObservationEvidence]:
    """Build competition evidence from REAL OpenStreetMap competitor POIs.

    This is the real-data path for the competition signal. `osm_elements` are the
    relevance-filtered competitor POIs returned by osm_service (each carries a
    `distance_km`). It is display/decision evidence only — it must NOT be fed into
    the ML feature vector (the model is trained on the simulation scale).

    Returns None when OSM was not live, so callers can fall back to the catalog
    seed or the formula proxy.
    """
    if not is_live:
        return None

    observed_count = len(osm_elements)
    density_per_10k = observed_count / max(1.0, population / 10000.0) if population > 0 else 0.0

    distances = [
        _safe_float(item.get("distance_km"), 0.0)
        for item in osm_elements
        if item.get("distance_km") is not None
    ]
    nearest = round(min(distances), 3) if distances else None

    pressure = _competition_pressure_index(observed_count, density_per_10k, nearest)

    return CompetitionObservationEvidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        source_name="OpenStreetMap (Overpass API)",
        source_method="Live count of matching businesses tagged in OpenStreetMap within the analysis radius",
        source_date=date.today().isoformat(),
        method="live_osm_competitor_scan",
        credibility="medium",
        observed_competitor_count=observed_count,
        competitor_density_per_10k=round(density_per_10k, 3),
        nearest_competitor_distance_km=nearest,
        avg_competitor_rating=None,
        chain_share_pct=None,
        competition_pressure_index=pressure,
        data_quality_note=(
            # The scan funnel travels with the number so "why 8 and not 60?" is answerable
            # from the UI: it says how many businesses were considered and how many
            # survived relevance scoring, instead of presenting a bare count.
            (scan_note + " " if scan_note else "")
            + "Real count of competitor businesses mapped in OpenStreetMap within the radius. "
            "OSM coverage varies by area and some businesses may be unmapped, so treat this as a "
            "strong but incomplete (lower-bound) observation, not a full census of the market."
        ),
    )


def apply_competition_observation_to_features(features: Dict[str, Any]) -> Dict[str, Any]:
    population = _safe_float(features.get("population_2021"), 0.0)
    evidence = get_competition_observation(
        municipality_name=str(features.get("municipality_name") or features.get("municipality") or ""),
        business_subcategory=str(features.get("business_subcategory") or ""),
        radius_km=_safe_float(features.get("radius_km"), 5.0),
        population=population,
    )

    # The current feature builder does not store municipality_name, so callers
    # normally set it before this function. If no data-backed row exists, keep
    # the previous model feature values but mark the source clearly.
    if evidence is None:
        features["competition_data_source"] = "feature_builder_proxy"
        features["competition_data_method"] = "formula_proxy_from_demographic_market_features"
        features["competition_data_credibility"] = "limited"
        return features

    features["competitor_count_estimate"] = evidence.observed_competitor_count
    features["competitor_density_per_10k"] = evidence.competitor_density_per_10k
    features["competition_score_0_100"] = evidence.competition_pressure_index
    features["nearest_competitor_distance_km"] = evidence.nearest_competitor_distance_km or 0.0
    features["avg_competitor_rating"] = evidence.avg_competitor_rating or 0.0
    features["chain_share_pct"] = evidence.chain_share_pct or 0.0
    features["competition_data_source"] = evidence.source_name
    features["competition_data_method"] = evidence.method
    features["competition_data_credibility"] = evidence.credibility
    features["competition_source_date"] = evidence.source_date
    features["competition_data_quality_note"] = evidence.data_quality_note
    return features


def list_competition_observations() -> List[CompetitionObservationEvidence]:
    df = _load_observations()
    if df.empty:
        return []

    observations: List[CompetitionObservationEvidence] = []
    for _, row in df.iterrows():
        population_placeholder = 10000.0
        observed_count = _safe_int(row.get("observed_count_5km"), 0)
        density = observed_count / max(1.0, population_placeholder / 10000.0)
        nearest = _safe_float(row.get("nearest_competitor_distance_km"), 0.0)
        observations.append(
            CompetitionObservationEvidence(
                municipality_name=str(row.get("municipality_name")),
                business_subcategory=str(row.get("business_subcategory")),
                source_name=str(row.get("source_name")),
                source_method=str(row.get("source_method")),
                source_date=str(row.get("source_date")),
                method="catalog_row_preview_5km",
                credibility="medium" if observed_count > 0 else "limited",
                observed_competitor_count=observed_count,
                competitor_density_per_10k=round(density, 3),
                nearest_competitor_distance_km=round(nearest, 2) if nearest else None,
                avg_competitor_rating=round(_safe_float(row.get("avg_competitor_rating")), 2),
                chain_share_pct=round(_safe_float(row.get("chain_share_pct")), 2),
                competition_pressure_index=_competition_pressure_index(observed_count, density, nearest),
                data_quality_note=str(row.get("data_quality_note")),
            )
        )

    return observations
