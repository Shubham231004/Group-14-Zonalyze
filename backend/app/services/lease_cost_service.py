from typing import Any, Dict

from app.schemas.dashboard import ModuleAnalysisResponse


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _level_from_pressure(pressure: float) -> str:
    if pressure >= 75:
        return "high"
    if pressure >= 50:
        return "medium"
    return "low"


def analyze_lease_cost(
    features: Dict[str, Any],
    prediction_result: Dict[str, Any] | None = None,
) -> ModuleAnalysisResponse:
    """
    Provides lease cost analysis using the Step 10 lease evidence fields.

    The score is not presented as a real commercial-rent truth. It is a cost
    pressure index supported by either a lease evidence catalog row or an
    explicitly marked fallback proxy.
    """
    median_lease = _safe_float(features.get("monthly_lease_cost_estimate"))
    low_lease = _safe_float(features.get("lease_cost_low_estimate"), median_lease * 0.82)
    high_lease = _safe_float(features.get("lease_cost_high_estimate"), median_lease * 1.22)
    rent_pressure = _safe_float(features.get("rent_pressure_index_0_100"), 50.0)
    lease_psf = _safe_float(features.get("lease_cost_per_sqft_year"))
    operating_cost = _safe_float(features.get("monthly_operating_cost_estimate"))

    predicted_revenue = 0.0
    if prediction_result:
        predicted_revenue = _safe_float(prediction_result.get("predicted_monthly_net_revenue"))

    # Net revenue can be negative, so use gross operating burden as context when
    # the predicted value is not suitable as a denominator.
    lease_burden_ratio = 0.0
    if operating_cost > 0:
        lease_burden_ratio = min(1.0, median_lease / operating_cost)

    score = min(100.0, max(0.0, rent_pressure * 0.58 + lease_burden_ratio * 100 * 0.42))
    level = _level_from_pressure(score)

    source_method = str(features.get("lease_data_method", "feature_fallback_proxy"))
    credibility = str(features.get("lease_data_credibility", "limited"))

    if source_method == "catalog_seed_proxy":
        summary = (
            f"Lease cost is represented as a range, with a median estimate of ${median_lease:,.0f}. "
            f"This comes from the lease evidence catalog, but it is still a seeded proxy until real commercial listings are connected."
        )
    elif source_method == "municipality_catalog_proxy":
        summary = (
            f"Lease cost is estimated from a municipality-level evidence row. The median estimate is ${median_lease:,.0f}, "
            "but the exact business subcategory does not yet have its own lease evidence row."
        )
    else:
        summary = (
            f"Lease cost is estimated as a fallback range with median ${median_lease:,.0f}. "
            "This should be treated cautiously until real commercial lease data is added."
        )

    signals = [
        f"Estimated lease range: ${low_lease:,.0f} to ${high_lease:,.0f} per month.",
        f"Rent pressure index is {rent_pressure:.1f}/100, producing a {level} cost-pressure reading.",
        f"Lease evidence method: {source_method}; credibility: {credibility}.",
    ]

    if lease_psf > 0:
        signals.append(f"Estimated annual lease cost is ${lease_psf:,.2f} per square foot.")
    if predicted_revenue < 0:
        signals.append("Predicted net revenue is negative, so lease burden should be reviewed carefully.")

    return ModuleAnalysisResponse(
        score=round(score, 2),
        level=level,
        summary=summary,
        signals=signals,
        metrics={
            "monthly_lease_cost_estimate": round(median_lease, 2),
            "low_monthly_lease_cost": round(low_lease, 2),
            "high_monthly_lease_cost": round(high_lease, 2),
            "lease_cost_per_sqft_year": round(lease_psf, 2),
            "rent_pressure_index": round(rent_pressure, 2),
            "lease_burden_ratio": round(lease_burden_ratio, 4),
        },
    )
