from typing import Any, Dict, List

from app.schemas.dashboard import PredictionExplanationResponse


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _score(value: float) -> str:
    return f"{value:.1f}/100"


def _add_factor(factors: List[str], condition: bool, text: str) -> None:
    if condition:
        factors.append(text)


def build_prediction_explanation(
    features: Dict[str, Any],
    prediction_result: Dict[str, Any],
) -> PredictionExplanationResponse:
    """
    Converts model inputs and outputs into plain-language explanations.

    The model still produces the prediction, but this service explains the
    main business factors behind the result so the dashboard does not feel
    like a black box.
    """
    competition_score = float(features.get("competition_score_0_100", 0))
    demand_score = float(features.get("demand_score_0_100", 0))
    demographic_fit_score = float(features.get("demographic_fit_score_0_100", 0))
    competitor_count = int(round(float(features.get("competitor_count_estimate", 0))))
    reachable_population = float(features.get("reachable_population_estimate", 0))
    lease_cost = float(features.get("monthly_lease_cost_estimate", 0))
    operating_cost = float(features.get("monthly_operating_cost_estimate", 0))
    revenue = float(prediction_result.get("predicted_monthly_net_revenue", 0))
    feasibility = float(prediction_result.get("predicted_feasibility_score", 0))
    risk_class = str(prediction_result.get("predicted_risk_class", "unknown"))
    recommendation = str(prediction_result.get("recommendation", "unknown"))

    positive_factors: List[str] = []
    negative_factors: List[str] = []

    _add_factor(
        positive_factors,
        demand_score >= 65,
        f"Demand proxy is strong for this business type with a demand score of {_score(demand_score)}.",
    )
    _add_factor(
        positive_factors,
        demographic_fit_score >= 65,
        f"The local demographic profile fits this business with a fit score of {_score(demographic_fit_score)}.",
    )
    _add_factor(
        positive_factors,
        competition_score < 40,
        f"Competition pressure estimate is manageable at {_score(competition_score)}.",
    )
    _add_factor(
        positive_factors,
        revenue > 0,
        f"The prototype model estimates positive monthly net revenue of {_money(revenue)}.",
    )
    _add_factor(
        positive_factors,
        reachable_population >= 25000,
        f"The selected radius reaches about {reachable_population:,.0f} people.",
    )

    _add_factor(
        negative_factors,
        demand_score < 45,
        f"Demand is limited for this scenario with a demand score of {_score(demand_score)}.",
    )
    _add_factor(
        negative_factors,
        demographic_fit_score < 45,
        f"The selected business type does not strongly match the local demographic profile.",
    )
    _add_factor(
        negative_factors,
        competition_score >= 65,
        f"Competition pressure estimate is high at {_score(competition_score)} with about {competitor_count} estimated competitors.",
    )
    _add_factor(
        negative_factors,
        revenue <= 0,
        f"The prototype model estimates negative monthly net revenue of {_money(revenue)}.",
    )
    _add_factor(
        negative_factors,
        lease_cost >= 9000,
        f"Estimated lease cost is high at {_money(lease_cost)} per month.",
    )
    _add_factor(
        negative_factors,
        operating_cost >= 35000,
        f"Estimated operating cost is high at {_money(operating_cost)} per month.",
    )

    if not positive_factors:
        positive_factors.append(
            "No major positive factor dominates this scenario, so the result should be treated carefully."
        )

    if not negative_factors:
        negative_factors.append(
            "No major negative factor dominates this scenario based on the current model inputs."
        )

    if revenue > 0:
        revenue_explanation = (
            f"The prototype model estimates positive monthly net revenue of {_money(revenue)}. "
            f"This is based on estimated demand, reachable population, average ticket size, and monthly operating costs."
        )
    else:
        revenue_explanation = (
            f"The prototype model estimates negative monthly net revenue of {_money(revenue)}. "
            f"This usually means the estimated demand is not high enough to cover lease, staff, utilities, marketing, and other operating costs."
        )

    if risk_class == "low":
        risk_explanation = (
            f"Prototype risk is low because the current model sees a stronger balance between demand, competition, and expected revenue. "
            f"Competition pressure is {_score(competition_score)} and demand is {_score(demand_score)}."
        )
    elif risk_class == "medium":
        risk_explanation = (
            f"Prototype risk is medium because the scenario has both strengths and weaknesses. "
            f"Demand is {_score(demand_score)}, while competition pressure is {_score(competition_score)}."
        )
    elif risk_class == "high":
        risk_explanation = (
            f"Prototype risk is high because the current model detected pressure from competition, costs, or weak revenue potential. "
            f"Competition pressure is {_score(competition_score)} and estimated operating cost is {_money(operating_cost)} per month."
        )
    else:
        risk_explanation = "Risk could not be explained because the model did not return a recognized risk class."

    if recommendation == "recommended":
        feasibility_explanation = (
            f"The scenario is recommended as decision support because the prototype feasibility estimate is {_score(feasibility)}, "
            f"the risk class is {risk_class}, and the predicted revenue is positive."
        )
    elif recommendation == "borderline":
        feasibility_explanation = (
            f"The scenario is borderline because the prototype feasibility estimate is {_score(feasibility)}. "
            f"It may still work, but the user should review cost and competition factors before making a decision."
        )
    else:
        feasibility_explanation = (
            f"The scenario is not recommended because the prototype feasibility estimate is {_score(feasibility)} "
            f"or the predicted risk and revenue combination is not strong enough."
        )

    return PredictionExplanationResponse(
        competition_score=round(competition_score, 2),
        demand_score=round(demand_score, 2),
        demographic_fit_score=round(demographic_fit_score, 2),
        estimated_competitor_count=competitor_count,
        reachable_population_estimate=round(reachable_population, 2),
        monthly_lease_cost_estimate=round(lease_cost, 2),
        monthly_operating_cost_estimate=round(operating_cost, 2),
        revenue_explanation=revenue_explanation,
        risk_explanation=risk_explanation,
        feasibility_explanation=feasibility_explanation,
        top_positive_factors=positive_factors[:4],
        top_negative_factors=negative_factors[:4],
    )
