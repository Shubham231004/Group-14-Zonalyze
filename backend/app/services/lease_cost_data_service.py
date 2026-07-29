from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from app.schemas.lease import LeaseCostEvidence


LEASE_COST_OBSERVATIONS_PATH = Path("app/data/market/lease_cost_observations_seed.csv")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "" or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize(value: str) -> str:
    return str(value or "").strip().lower()


def _pressure_level(index: float) -> str:
    if index >= 75:
        return "high"
    if index >= 50:
        return "medium"
    return "low"


def _row_to_evidence(row: pd.Series) -> LeaseCostEvidence:
    return LeaseCostEvidence(
        municipality_name=str(row.get("municipality_name", "")),
        business_subcategory=str(row.get("business_subcategory", "")),
        source_name=str(row.get("source_name", "Zonalyze lease evidence catalog")),
        source_method=str(row.get("source_method", "Catalog-backed lease proxy")),
        source_date=str(row.get("source_date", "unknown")),
        method=str(row.get("method", "catalog_seed_proxy")),
        credibility=str(row.get("credibility", "medium")),
        estimated_space_sqft=_safe_float(row.get("estimated_space_sqft")),
        low_monthly_lease_cost=_safe_float(row.get("low_monthly_lease_cost")),
        median_monthly_lease_cost=_safe_float(row.get("median_monthly_lease_cost")),
        high_monthly_lease_cost=_safe_float(row.get("high_monthly_lease_cost")),
        lease_cost_per_sqft_year=_safe_float(row.get("lease_cost_per_sqft_year")),
        rent_pressure_index=_safe_float(row.get("rent_pressure_index")),
        commercial_cost_pressure_level=str(row.get("commercial_cost_pressure_level", "medium")),
        data_quality_note=str(row.get("data_quality_note", "Seeded lease proxy. Replace with real commercial lease data when available.")),
    )


def _fallback_from_features(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
    features: Dict[str, Any],
) -> LeaseCostEvidence:
    """
    Returns an explicit fallback range when the catalog has no scenario row.

    This is still a proxy, but it is better than returning one hidden formula
    value because the user can see the estimated range and credibility level.
    """
    median = _safe_float(features.get("monthly_lease_cost_estimate"), 2500.0)
    rent_pressure = _safe_float(features.get("rent_pressure_index_0_100"), 50.0)
    sqft = _safe_float(features.get("estimated_space_sqft"), 1000.0)

    radius_adjustment = 1.0
    if radius_km <= 1:
        radius_adjustment = 1.05
    elif radius_km >= 10:
        radius_adjustment = 0.92

    median = max(750.0, median * radius_adjustment)
    spread = 0.18 + (rent_pressure / 100.0) * 0.12
    low = median * (1 - spread)
    high = median * (1 + spread)
    annual_psf = (median * 12) / max(sqft, 1)

    return LeaseCostEvidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        source_name="Zonalyze feature fallback",
        source_method="Fallback range generated from rent pressure index, business space requirement, and existing feature estimate",
        source_date="runtime",
        method="feature_fallback_proxy",
        credibility="limited",
        estimated_space_sqft=round(sqft, 2),
        low_monthly_lease_cost=round(low, 2),
        median_monthly_lease_cost=round(median, 2),
        high_monthly_lease_cost=round(high, 2),
        lease_cost_per_sqft_year=round(annual_psf, 2),
        rent_pressure_index=round(rent_pressure, 2),
        commercial_cost_pressure_level=_pressure_level(rent_pressure),
        data_quality_note="No lease evidence row exists for this scenario yet. This range is an explicit proxy and should be replaced with commercial listing or broker data.",
    )


def load_lease_cost_observations() -> pd.DataFrame:
    if not LEASE_COST_OBSERVATIONS_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(LEASE_COST_OBSERVATIONS_PATH)


def list_lease_cost_observations() -> List[LeaseCostEvidence]:
    df = load_lease_cost_observations()
    if df.empty:
        return []
    return [_row_to_evidence(row) for _, row in df.iterrows()]


def get_lease_cost_evidence(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
    features: Dict[str, Any],
) -> LeaseCostEvidence:
    df = load_lease_cost_observations()
    if not df.empty:
        exact = df[
            (df["municipality_name"].map(_normalize) == _normalize(municipality_name))
            & (df["business_subcategory"].map(_normalize) == _normalize(business_subcategory))
        ]
        if not exact.empty:
            return _row_to_evidence(exact.iloc[0])

        municipality_only = df[
            df["municipality_name"].map(_normalize) == _normalize(municipality_name)
        ]
        if not municipality_only.empty:
            row = municipality_only.iloc[0].copy()
            row["business_subcategory"] = business_subcategory
            row["source_method"] = (
                "Municipality-level lease proxy. Exact business subcategory row was not available, "
                "so a local lease pressure row was reused as a fallback."
            )
            row["method"] = "municipality_catalog_proxy"
            row["credibility"] = "limited-medium"
            row["data_quality_note"] = "Municipality has lease evidence, but this exact business subcategory does not."
            return _row_to_evidence(row)

    return _fallback_from_features(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
        features=features,
    )


def apply_lease_cost_evidence_to_features(
    features: Dict[str, Any],
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
) -> Dict[str, Any]:
    evidence = get_lease_cost_evidence(
        municipality_name=municipality_name,
        business_subcategory=business_subcategory,
        radius_km=radius_km,
        features=features,
    )

    updated = dict(features)
    previous_lease = _safe_float(updated.get("monthly_lease_cost_estimate"))
    updated["monthly_lease_cost_estimate"] = evidence.median_monthly_lease_cost
    updated["lease_cost_low_estimate"] = evidence.low_monthly_lease_cost
    updated["lease_cost_high_estimate"] = evidence.high_monthly_lease_cost
    updated["lease_cost_per_sqft_year"] = evidence.lease_cost_per_sqft_year
    updated["lease_data_source"] = evidence.source_name
    updated["lease_data_method"] = evidence.method
    updated["lease_data_credibility"] = evidence.credibility
    updated["lease_cost_pressure_level"] = evidence.commercial_cost_pressure_level

    # Preserve operating-cost consistency when lease cost changes. The feature
    # builder already creates operating cost, so only adjust the lease delta.
    operating = _safe_float(updated.get("monthly_operating_cost_estimate"))
    if operating > 0 and previous_lease > 0:
        updated["monthly_operating_cost_estimate"] = round(
            max(0.0, operating - previous_lease + evidence.median_monthly_lease_cost),
            2,
        )

    return updated
