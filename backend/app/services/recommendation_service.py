from app.schemas.competition import CompetitionObservationEvidence
from app.schemas.demand import DemandEvidence
from app.schemas.lease import LeaseCostEvidence
from app.schemas.dashboard import PredictionCredibilityResponse
from app.schemas.recommendation import RecommendationDecision, RecommendationEvidenceSignal


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _confidence_level(score: float) -> str:
    if score >= 75:
        return "strong"
    if score >= 55:
        return "moderate"
    if score >= 35:
        return "limited"
    return "weak"


def _risk_probability(prediction_result: dict, risk_class: str) -> float:
    probabilities = prediction_result.get("risk_probabilities") or {}
    return float(probabilities.get(risk_class, 0.0) or 0.0)


def _evidence_quality_bonus(
    competition_evidence: CompetitionObservationEvidence | None,
    lease_cost_evidence: LeaseCostEvidence | None,
    demand_evidence: DemandEvidence | None,
) -> float:
    credibility_map = {
        "high": 10.0,
        "medium": 6.0,
        "low": 2.5,
        "limited": 1.0,
    }
    values = []
    for item in (competition_evidence, lease_cost_evidence, demand_evidence):
        if item is None:
            values.append(0.0)
        else:
            values.append(credibility_map.get(str(item.credibility).lower(), 2.0))
    return sum(values) / max(len(values), 1)


def _money(value: float | int | None) -> str:
    if value is None:
        return "not available"
    return f"${value:,.0f}"


def build_recommendation_decision(
    *,
    features: dict,
    prediction_result: dict,
    credibility: PredictionCredibilityResponse | None,
    competition_evidence: CompetitionObservationEvidence | None,
    lease_cost_evidence: LeaseCostEvidence | None,
    demand_evidence: DemandEvidence | None,
) -> RecommendationDecision:
    """
    Converts model output and evidence quality into a user-facing decision.

    This is intentionally not a simple threshold on one score. The decision
    considers model predictions, risk probability, revenue, evidence quality,
    and confidence. It also explains which signals support or weaken the result.
    """
    predicted_revenue = float(prediction_result.get("predicted_monthly_net_revenue", 0.0) or 0.0)
    predicted_feasibility = float(prediction_result.get("predicted_feasibility_score", 0.0) or 0.0)
    predicted_risk = str(prediction_result.get("predicted_risk_class", "medium") or "medium").lower()

    high_risk_prob = _risk_probability(prediction_result, "high")
    low_risk_prob = _risk_probability(prediction_result, "low")

    demand_index = float(
        demand_evidence.demand_pressure_index
        if demand_evidence is not None
        else features.get("demand_score_0_100", 0.0)
        or 0.0
    )
    competition_index = float(
        competition_evidence.competition_pressure_index
        if competition_evidence is not None
        else features.get("competition_score_0_100", 0.0)
        or 0.0
    )
    lease_median = float(
        lease_cost_evidence.median_monthly_lease_cost
        if lease_cost_evidence is not None
        else features.get("estimated_monthly_lease_cost", 0.0)
        or 0.0
    )

    revenue_strength = 30.0 if predicted_revenue > 15000 else 18.0 if predicted_revenue > 5000 else 7.0 if predicted_revenue > 0 else -8.0
    feasibility_strength = (predicted_feasibility - 50.0) * 0.55
    demand_strength = (demand_index - 50.0) * 0.25
    competition_penalty = max(0.0, competition_index - 55.0) * 0.25
    lease_penalty = 12.0 if lease_median > 9000 else 7.0 if lease_median > 6500 else 2.0 if lease_median > 4000 else 0.0
    risk_penalty = 22.0 if predicted_risk == "high" else 10.0 if predicted_risk == "medium" else 0.0
    high_risk_penalty = high_risk_prob * 16.0
    evidence_bonus = _evidence_quality_bonus(competition_evidence, lease_cost_evidence, demand_evidence)

    decision_score = _clamp(
        50.0
        + revenue_strength
        + feasibility_strength
        + demand_strength
        + evidence_bonus
        - competition_penalty
        - lease_penalty
        - risk_penalty
        - high_risk_penalty
    )

    if decision_score >= 70 and predicted_risk != "high" and predicted_revenue > 0:
        final_recommendation = "recommended"
        recommendation_label = "Decision-Support Recommended"
        action_guidance = "This scenario is worth moving into a deeper planning stage, including direct competitor checks, site visits, and updated cost quotes."
    elif decision_score >= 45:
        final_recommendation = "borderline"
        recommendation_label = "Decision-Support Borderline / Needs Review"
        action_guidance = "This scenario should not be rejected immediately, but the user should verify the weak signals before investing."
    else:
        final_recommendation = "not_recommended"
        recommendation_label = "Decision-Support Not Recommended"
        action_guidance = "This scenario should be treated cautiously unless better data or a different location changes the risk profile."

    credibility_score = float(credibility.overall_confidence_score if credibility else 45.0)
    decision_confidence = _clamp((credibility_score * 0.7) + (decision_score * 0.3))
    confidence_level = _confidence_level(decision_confidence)

    strengths: list[str] = []
    concerns: list[str] = []

    if predicted_revenue > 0:
        strengths.append(f"The model predicts positive monthly net revenue of {_money(predicted_revenue)}.")
    else:
        concerns.append(f"The prototype model estimates negative monthly net revenue of {_money(predicted_revenue)}.")

    if predicted_feasibility >= 70:
        strengths.append(f"The feasibility score is strong at {predicted_feasibility:.1f}/100.")
    elif predicted_feasibility < 50:
        concerns.append(f"The prototype feasibility estimate is weak at {predicted_feasibility:.1f}/100.")

    if demand_index >= 65:
        strengths.append(f"Demand evidence is favourable with a demand pressure index of {demand_index:.1f}/100.")
    elif demand_index < 45:
        concerns.append(f"Demand evidence is weak with a demand pressure index of {demand_index:.1f}/100.")

    if competition_index >= 65:
        concerns.append(f"Competition pressure estimate is high at {competition_index:.1f}/100.")
    elif competition_index < 40:
        strengths.append(f"Competition pressure estimate is relatively low at {competition_index:.1f}/100.")

    if lease_median > 8000:
        concerns.append(f"The median monthly lease estimate is high at {_money(lease_median)}.")
    elif lease_median > 0 and lease_median < 5000:
        strengths.append(f"The median monthly lease estimate is manageable at {_money(lease_median)}.")

    if high_risk_prob >= 0.45:
        concerns.append(f"The prototype risk model assigns a high-risk probability of {high_risk_prob * 100:.1f}%.")
    elif low_risk_prob >= 0.45:
        strengths.append(f"The prototype risk model assigns a low-risk probability of {low_risk_prob * 100:.1f}%.")

    if not strengths:
        strengths.append("No strong positive signal dominates this scenario yet.")
    if not concerns:
        concerns.append("No major concern dominates this scenario, but external market validation is still required.")

    evidence_signals = [
        RecommendationEvidenceSignal(
            name="Prototype monthly net revenue estimate",
            value=_money(predicted_revenue),
            direction="positive" if predicted_revenue > 0 else "negative",
            impact="high",
            source_type="model_prediction",
        ),
        RecommendationEvidenceSignal(
            name="Prototype feasibility estimate",
            value=f"{predicted_feasibility:.1f}/100",
            direction="positive" if predicted_feasibility >= 60 else "negative" if predicted_feasibility < 45 else "mixed",
            impact="high",
            source_type="model_prediction",
        ),
        RecommendationEvidenceSignal(
            name="Competition pressure estimate",
            value=f"{competition_index:.1f}/100",
            direction="negative" if competition_index >= 65 else "positive" if competition_index < 40 else "mixed",
            impact="medium",
            source_type="evidence_or_proxy",
        ),
        RecommendationEvidenceSignal(
            name="Demand proxy index",
            value=f"{demand_index:.1f}/100",
            direction="positive" if demand_index >= 65 else "negative" if demand_index < 45 else "mixed",
            impact="medium",
            source_type="evidence_or_proxy",
        ),
        RecommendationEvidenceSignal(
            name="Lease cost range",
            value=_money(lease_median),
            direction="negative" if lease_median > 8000 else "positive" if 0 < lease_median < 5000 else "mixed",
            impact="medium",
            source_type="evidence_or_proxy",
        ),
    ]

    decision_summary = (
        f"{recommendation_label} with {confidence_level} decision confidence. "
        f"The decision score is {decision_score:.1f}/100 and combines prototype model predictions, evidence signals, and data credibility."
    )
    decision_rationale = (
        f"The decision-support recommendation is based on prototype revenue estimates, feasibility, risk probability, demand evidence, "
        f"competition evidence, lease-cost evidence, and the current credibility profile. "
        f"It should be treated as decision support, not as a guarantee of business outcome."
    )

    caution_note = (
        "This recommendation is still limited by the available evidence. It becomes more reliable when real competitor listings, "
        "commercial lease observations, mobility or foot-traffic data, and real business performance outcomes are added."
    )

    return RecommendationDecision(
        final_recommendation=final_recommendation,
        recommendation_label=recommendation_label,
        decision_confidence_score=round(decision_confidence, 2),
        confidence_level=confidence_level,
        decision_summary=decision_summary,
        decision_rationale=decision_rationale,
        action_guidance=action_guidance,
        major_strengths=strengths[:5],
        major_concerns=concerns[:5],
        evidence_signals=evidence_signals,
        caution_note=caution_note,
    )
