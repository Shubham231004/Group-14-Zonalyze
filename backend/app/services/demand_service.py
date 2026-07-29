from typing import Any, Dict

from app.schemas.dashboard import ModuleAnalysisResponse


def _level_from_score(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 50:
        return "moderate"
    return "weak"


def analyze_demand(features: Dict[str, Any]) -> ModuleAnalysisResponse:
    """
    Summarizes demand evidence for the selected scenario.

    This is not treated as a final real-world demand prediction.
    It summarizes the current demand signals available to Zonalyze,
    including census-backed population values and proxy-based demand signals.
    """

    demand_score = float(
        features.get("demand_pressure_index")
        or features.get("demand_score_0_100")
        or features.get("demographic_fit_score")
        or 0
    )

    reachable_population = float(
        features.get("reachable_population_estimate")
        or features.get("population_2021")
        or 0
    )

    target_customer_pool = float(
        features.get("target_customer_pool_estimate")
        or reachable_population * 0.04
    )

    demographic_fit = float(
        features.get("demographic_fit_score")
        or features.get("business_type_demographic_fit")
        or demand_score
    )

    foot_traffic_proxy = float(
        features.get("foot_traffic_proxy_index")
        or features.get("foot_traffic_proxy")
        or 50
    )

    transit_access_proxy = float(
        features.get("transit_access_proxy_index")
        or features.get("transit_access_score")
        or 50
    )

    level = _level_from_score(demand_score)

    if level == "strong":
        summary = (
            "Demand proxy signals are strong for this scenario based on reachable "
            "population, demographic fit, and local activity proxy signals."
        )
    elif level == "moderate":
        summary = (
            "Demand proxy signals are moderate. The scenario shows usable customer "
            "potential, but real foot-traffic or transaction data would improve confidence."
        )
    else:
        summary = (
            "Demand proxy signals are weak. The selected area and business type may need "
            "stronger validation before being treated as a strong opportunity."
        )

    return ModuleAnalysisResponse(
        score=round(demand_score, 2),
        level=level,
        summary=summary,
        signals=[
            f"Reachable population proxy: {reachable_population:,.0f}",
            f"Target customer pool proxy: {target_customer_pool:,.0f}",
            f"Demographic fit proxy: {demographic_fit:.1f}/100",
            f"Foot-traffic proxy index: {foot_traffic_proxy:.1f}/100",
            f"Transit access proxy index: {transit_access_proxy:.1f}/100",
        ],
        metrics={
            "reachable_population_estimate": round(reachable_population, 2),
            "target_customer_pool_estimate": round(target_customer_pool, 2),
            "demographic_fit_score": round(demographic_fit, 2),
            "foot_traffic_proxy_index": round(foot_traffic_proxy, 2),
            "transit_access_proxy_index": round(transit_access_proxy, 2),
            "demand_pressure_index": round(demand_score, 2),
        },
    )