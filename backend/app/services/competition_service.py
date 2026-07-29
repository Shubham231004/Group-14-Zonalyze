from typing import Any, Dict, List

from app.schemas.dashboard import ModuleAnalysisResponse
from app.services.competition_data_service import get_competition_observation


def _level_from_score(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"


def analyze_competition(features: Dict[str, Any]) -> ModuleAnalysisResponse:
    """
    Builds a competition-focused interpretation from the best available
    competition signal.

    Step 9 improves the previous proxy-only method. If a catalog observation is
    available for the selected municipality and business subcategory, the score
    is based on that observation. If no observation exists, the service falls
    back to the older feature-builder proxy and clearly labels that limitation.
    """
    score = float(features.get("competition_score_0_100", 0))
    competitor_count = float(features.get("competitor_count_estimate", 0))
    competitor_density = float(features.get("competitor_density_per_10k", 0))
    market_index = float(features.get("market_base_index_0_100", 0))
    radius = float(features.get("radius_km", 0))
    source = str(features.get("competition_data_source", "feature_builder_proxy"))
    method = str(features.get("competition_data_method", "formula_proxy"))
    credibility = str(features.get("competition_data_credibility", "limited"))
    nearest_distance = float(features.get("nearest_competitor_distance_km", 0) or 0)

    signals: List[str] = []

    if source != "feature_builder_proxy":
        signals.append(
            f"Competition uses a market observation catalog source: {source}."
        )
        signals.append(
            f"The selected radius contains about {competitor_count:.0f} same-category competitors based on the current evidence/catalog row."
        )
        if nearest_distance > 0:
            signals.append(
                f"The nearest same-category competitor is approximately {nearest_distance:.1f} km away."
            )
    else:
        signals.append(
            "No competition observation row was found for this exact scenario, so the system used the fallback proxy estimate, which should be treated as limited-confidence evidence."
        )
        signals.append(
            f"The fallback method estimates about {competitor_count:.0f} relevant competitors inside the selected radius."
        )

    if competitor_density >= 6:
        signals.append(
            f"Competitor density is high at {competitor_density:.2f} competitors per 10,000 people."
        )
    elif competitor_density >= 2.5:
        signals.append(
            f"Competitor density is moderate at {competitor_density:.2f} competitors per 10,000 people."
        )
    else:
        signals.append(
            f"Competitor density is manageable at {competitor_density:.2f} competitors per 10,000 people."
        )

    if market_index >= 70:
        signals.append(
            "The municipality has a strong market base, which can attract both demand and competitors."
        )
    elif market_index < 40:
        signals.append(
            "The municipality has a smaller market base, so competition may be lower but demand may also be limited."
        )

    level = _level_from_score(score)
    summary = (
        f"Competition pressure estimate is {level} with a derived proxy index of {score:.1f}/100. "
        f"Source credibility is {credibility}. Method: {method}."
    )

    return ModuleAnalysisResponse(
        score=round(score, 2),
        level=level,
        summary=summary,
        signals=signals,
        metrics={
            "observed_or_estimated_competitor_count": round(competitor_count, 2),
            "competitor_density_per_10k": round(competitor_density, 3),
            "market_base_index": round(market_index, 2),
            "radius_km": round(radius, 2),
            "nearest_competitor_distance_km": round(nearest_distance, 2),
        },
    )
