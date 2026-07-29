from __future__ import annotations

from typing import Any, Dict, List, Tuple


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _risk_rank(label: str) -> int:
    return RISK_ORDER.get(str(label).lower(), 1)


def _risk_from_rank(rank: int) -> str:
    if rank <= 0:
        return "low"
    if rank == 1:
        return "medium"
    return "high"


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _normalized_probabilities(
    original: Dict[str, float],
    adjusted_risk: str,
    minimum_probability: float,
) -> Dict[str, float]:
    """Return a conservative probability set after a consistency correction.

    The goal is not to pretend the model originally produced these probabilities.
    It is to avoid a UI contradiction where the adjusted class is not reflected in
    the probability display. The consistency note preserves the fact that this was
    post-processed.
    """
    probs = {"low": 0.0, "medium": 0.0, "high": 0.0}
    for key, value in (original or {}).items():
        label = str(key).lower()
        if label in probs:
            try:
                probs[label] = float(value)
            except Exception:
                probs[label] = 0.0

    current = probs.get(adjusted_risk, 0.0)
    if current >= minimum_probability:
        total = sum(probs.values()) or 1.0
        return {key: round(_clamp(value / total), 4) for key, value in probs.items()}

    remaining_mass = max(0.0, 1.0 - minimum_probability)
    other_total = sum(value for key, value in probs.items() if key != adjusted_risk)

    new_probs = {}
    for key, value in probs.items():
        if key == adjusted_risk:
            new_probs[key] = minimum_probability
        else:
            new_probs[key] = remaining_mass * (value / other_total) if other_total > 0 else remaining_mass / 2

    total = sum(new_probs.values()) or 1.0
    return {key: round(_clamp(value / total), 4) for key, value in new_probs.items()}


def apply_prediction_consistency_guard(
    *,
    prediction_result: Dict[str, Any],
    features: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply a transparent post-model consistency guard.

    The ML model remains the source of the raw prediction. This guard only handles
    obvious contradictions, for example a severe negative revenue prediction and
    near-zero feasibility being labelled low risk.
    """
    adjusted = dict(prediction_result)

    raw_risk = str(adjusted.get("predicted_risk_class", "medium") or "medium").lower()
    adjusted_risk = raw_risk if raw_risk in RISK_ORDER else "medium"

    revenue = float(adjusted.get("predicted_monthly_net_revenue", 0.0) or 0.0)
    feasibility = float(adjusted.get("predicted_feasibility_score", 0.0) or 0.0)
    probabilities = adjusted.get("risk_probabilities") or {}
    high_prob = float(probabilities.get("high", 0.0) or 0.0)
    low_prob = float(probabilities.get("low", 0.0) or 0.0)

    demand = float(
        features.get("demand_pressure_index")
        or features.get("demand_score_0_100")
        or 0.0
    )
    competition = float(
        features.get("competition_pressure_index")
        or features.get("competition_score_0_100")
        or 0.0
    )
    lease_burden = float(features.get("lease_burden_ratio", 0.0) or 0.0)
    profit_margin_pct = float(features.get("profit_margin_pct", 0.0) or 0.0)

    warnings: List[str] = []
    rules_triggered: List[str] = []

    def raise_risk_at_least(minimum: str, reason: str, rule_id: str) -> None:
        nonlocal adjusted_risk
        if _risk_rank(adjusted_risk) < _risk_rank(minimum):
            adjusted_risk = minimum
            warnings.append(reason)
            rules_triggered.append(rule_id)

    def lower_risk_at_most(maximum: str, reason: str, rule_id: str) -> None:
        nonlocal adjusted_risk
        if _risk_rank(adjusted_risk) > _risk_rank(maximum):
            adjusted_risk = maximum
            warnings.append(reason)
            rules_triggered.append(rule_id)

    # Severe contradiction: weak/negative financial outcome cannot be low risk.
    if revenue <= -10000 or feasibility < 25:
        raise_risk_at_least(
            "high",
            (
                f"Risk was raised because predicted revenue is {_money(revenue)} "
                f"and feasibility is {feasibility:.1f}/100."
            ),
            "severe_negative_financial_outcome",
        )
    elif revenue <= -2500 or feasibility < 42:
        raise_risk_at_least(
            "medium",
            (
                f"Risk was raised because predicted revenue is {_money(revenue)} "
                f"or feasibility is weak at {feasibility:.1f}/100."
            ),
            "weak_financial_outcome",
        )

    # Strong high-risk probability from the classifier should dominate.
    if high_prob >= 0.55:
        raise_risk_at_least(
            "high",
            f"Risk was raised because model high-risk probability is {high_prob * 100:.1f}%.",
            "high_risk_probability",
        )
    elif high_prob >= 0.40 and adjusted_risk == "low":
        raise_risk_at_least(
            "medium",
            f"Risk was raised because high-risk probability is still material at {high_prob * 100:.1f}%.",
            "material_high_risk_probability",
        )

    # Lease/competition stress can prevent low-risk classification.
    if adjusted_risk == "low" and (lease_burden >= 0.30 or competition >= 75):
        raise_risk_at_least(
            "medium",
            (
                f"Risk was raised because lease burden ({lease_burden:.2f}) or "
                f"competition pressure ({competition:.1f}/100) is elevated."
            ),
            "cost_or_competition_stress",
        )

    # Very strong financials can soften high-risk only when high-risk probability is not dominant.
    if (
        revenue >= 12000
        and feasibility >= 72
        and demand >= 65
        and high_prob < 0.45
        and profit_margin_pct >= 12
    ):
        lower_risk_at_most(
            "medium",
            (
                f"Risk was softened because revenue ({_money(revenue)}), feasibility "
                f"({feasibility:.1f}/100), and demand ({demand:.1f}/100) are strong."
            ),
            "strong_financial_and_demand_signals",
        )

    consistency_adjusted = adjusted_risk != raw_risk

    if consistency_adjusted:
        minimum_probability = 0.58 if adjusted_risk == "high" else 0.50
        adjusted["risk_probabilities"] = _normalized_probabilities(
            probabilities,
            adjusted_risk=adjusted_risk,
            minimum_probability=minimum_probability,
        )
        adjusted["predicted_risk_class"] = adjusted_risk

    adjusted["risk_class_before_consistency"] = raw_risk
    adjusted["consistency_adjusted"] = consistency_adjusted
    adjusted["consistency_status"] = "adjusted" if consistency_adjusted else "passed"
    adjusted["consistency_rules_triggered"] = rules_triggered
    adjusted["consistency_warnings"] = warnings

    if consistency_adjusted:
        adjusted["consistency_note"] = (
            "The raw model risk class was adjusted by a post-prediction consistency guard "
            "because the risk label conflicted with revenue, feasibility, probability, "
            "lease, demand, or competition signals."
        )
    else:
        adjusted["consistency_note"] = (
            "The raw model outputs passed the post-prediction consistency guard."
        )

    return adjusted
