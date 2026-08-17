import math
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.scenario_history import ScenarioHistoryRecord
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.scenario_history import (
    ScenarioComparisonItem,
    ScenarioComparisonResponse,
    ScenarioHistoryItem,
    ScenarioHistoryResponse,
)

_MAX_HISTORY_ITEMS = 25


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def _saved_at_to_iso(value: Any) -> str:
    if value is None:
        return _now_iso()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _history_item_from_record(record: ScenarioHistoryRecord) -> ScenarioHistoryItem:
    return ScenarioHistoryItem(
        scenario_id=record.scenario_id,
        saved_at=_saved_at_to_iso(record.saved_at),
        municipality_name=record.municipality_name,
        business_subcategory=record.business_subcategory,
        radius_km=float(record.radius_km),
        predicted_monthly_net_revenue=_safe_float(record.predicted_monthly_net_revenue),
        predicted_risk_class=record.predicted_risk_class,
        predicted_feasibility_score=_safe_float(record.predicted_feasibility_score),
        recommendation_label=record.recommendation_label,
        decision_confidence_score=_safe_float(record.decision_confidence_score),
        prediction_confidence_score=_safe_float(record.prediction_confidence_score),
        demand_pressure_index=_safe_float(record.demand_pressure_index),
        competition_pressure_index=_safe_float(record.competition_pressure_index),
        median_monthly_lease_cost=_safe_float(record.median_monthly_lease_cost),
        data_reliability_note=record.data_reliability_note,
    )


def _history_item_from_dashboard(dashboard: DashboardSummaryResponse) -> ScenarioHistoryItem:
    ml = dashboard.ml_prediction
    credibility = dashboard.prediction_credibility
    recommendation = dashboard.recommendation_decision
    demand = dashboard.demand_evidence
    competition = dashboard.competition_evidence
    lease = dashboard.lease_cost_evidence

    confidence = (
        recommendation.decision_confidence_score
        if recommendation is not None
        else credibility.overall_confidence_score if credibility is not None
        else None
    )

    reliability_note = (
        "Saved scenario uses census-backed demographics with model-predicted outputs and evidence/proxy layers for demand, competition, and lease cost."
    )
    if credibility is not None:
        reliability_note = credibility.user_facing_disclaimer

    return ScenarioHistoryItem(
        scenario_id=f"scn_{uuid4().hex[:10]}",
        saved_at=_now_iso(),
        municipality_name=dashboard.municipality_name,
        business_subcategory=dashboard.business_subcategory,
        radius_km=dashboard.radius_km,
        predicted_monthly_net_revenue=_safe_float(ml.predicted_monthly_net_revenue if ml else None),
        predicted_risk_class=ml.predicted_risk_class if ml else None,
        predicted_feasibility_score=_safe_float(ml.predicted_feasibility_score if ml else None),
        recommendation_label=recommendation.recommendation_label if recommendation else (ml.recommendation if ml else None),
        decision_confidence_score=_safe_float(confidence),
        prediction_confidence_score=_safe_float(credibility.overall_confidence_score if credibility else None),
        demand_pressure_index=_safe_float(demand.demand_pressure_index if demand else None),
        competition_pressure_index=_safe_float(competition.competition_pressure_index if competition else None),
        median_monthly_lease_cost=_safe_float(lease.median_monthly_lease_cost if lease else None),
        data_reliability_note=reliability_note,
    )


def _record_from_item(item: ScenarioHistoryItem) -> ScenarioHistoryRecord:
    return ScenarioHistoryRecord(
        scenario_id=item.scenario_id,
        municipality_name=item.municipality_name,
        business_subcategory=item.business_subcategory,
        radius_km=item.radius_km,
        predicted_monthly_net_revenue=item.predicted_monthly_net_revenue,
        predicted_risk_class=item.predicted_risk_class,
        predicted_feasibility_score=item.predicted_feasibility_score,
        recommendation_label=item.recommendation_label,
        decision_confidence_score=item.decision_confidence_score,
        prediction_confidence_score=item.prediction_confidence_score,
        demand_pressure_index=item.demand_pressure_index,
        competition_pressure_index=item.competition_pressure_index,
        median_monthly_lease_cost=item.median_monthly_lease_cost,
        data_reliability_note=item.data_reliability_note,
    )


def save_dashboard_to_history(
    dashboard: DashboardSummaryResponse, db: Session, user_id: str | None = None
) -> ScenarioHistoryItem:
    item = _history_item_from_dashboard(dashboard)
    record = _record_from_item(item)
    record.user_id = user_id
    db.add(record)
    db.commit()
    db.refresh(record)

    # Keep each user's history small. Newest 25 are kept (== None -> IS NULL,
    # i.e. the shared anonymous history when auth is off).
    older_records = (
        db.query(ScenarioHistoryRecord)
        .filter(ScenarioHistoryRecord.user_id == user_id)
        .order_by(ScenarioHistoryRecord.saved_at.desc(), ScenarioHistoryRecord.id.desc())
        .offset(_MAX_HISTORY_ITEMS)
        .all()
    )
    for older in older_records:
        db.delete(older)
    if older_records:
        db.commit()

    return _history_item_from_record(record)


def list_saved_scenarios(db: Session, user_id: str | None = None) -> ScenarioHistoryResponse:
    records = (
        db.query(ScenarioHistoryRecord)
        .filter(ScenarioHistoryRecord.user_id == user_id)
        .order_by(ScenarioHistoryRecord.saved_at.desc(), ScenarioHistoryRecord.id.desc())
        .limit(_MAX_HISTORY_ITEMS)
        .all()
    )
    items = [_history_item_from_record(record) for record in records]
    return ScenarioHistoryResponse(count=len(items), scenarios=items)


def clear_saved_scenarios(db: Session, user_id: str | None = None) -> ScenarioHistoryResponse:
    db.query(ScenarioHistoryRecord).filter(ScenarioHistoryRecord.user_id == user_id).delete()
    db.commit()
    return ScenarioHistoryResponse(count=0, scenarios=[])


def delete_saved_scenario(
    scenario_id: str, db: Session, user_id: str | None = None
) -> ScenarioHistoryResponse:
    record = (
        db.query(ScenarioHistoryRecord)
        .filter(
            ScenarioHistoryRecord.scenario_id == scenario_id,
            ScenarioHistoryRecord.user_id == user_id,
        )
        .first()
    )
    if record is not None:
        db.delete(record)
        db.commit()
    return list_saved_scenarios(db, user_id=user_id)


def _risk_points(risk_class: str | None) -> float:
    if risk_class == "low":
        return 92.0
    if risk_class == "medium":
        return 62.0
    if risk_class == "high":
        return 28.0
    return 50.0


def _revenue_points(revenue: float | None) -> float:
    if revenue is None:
        return 45.0
    return max(0.0, min(100.0, ((revenue + 25000.0) / 85000.0) * 100.0))


def _confidence_points(confidence: float | None) -> float:
    if confidence is None:
        return 50.0
    return max(0.0, min(100.0, confidence))


def _tradeoff_text(item: ScenarioHistoryItem) -> str:
    revenue = item.predicted_monthly_net_revenue
    risk = item.predicted_risk_class or "unknown"
    feasibility = item.predicted_feasibility_score
    confidence = item.decision_confidence_score or item.prediction_confidence_score

    parts = []
    if revenue is not None:
        parts.append(f"monthly net revenue estimate is ${revenue:,.0f}")
    if feasibility is not None:
        parts.append(f"feasibility score is {feasibility:.1f}/100")
    parts.append(f"risk class is {risk}")
    if confidence is not None:
        parts.append(f"decision confidence is {confidence:.1f}/100")
    return "; ".join(parts) + "."


def compare_saved_scenarios(db: Session, user_id: str | None = None) -> ScenarioComparisonResponse:
    scenarios = list_saved_scenarios(db, user_id=user_id).scenarios
    generated_at = _now_iso()

    if len(scenarios) == 0:
        return ScenarioComparisonResponse(
            generated_at=generated_at,
            compared_count=0,
            best_overall_scenario_id=None,
            comparison_summary="No saved scenarios are available for comparison yet.",
            rankings=[],
        )

    revenue_sorted = sorted(
        scenarios,
        key=lambda x: x.predicted_monthly_net_revenue if x.predicted_monthly_net_revenue is not None else -10**12,
        reverse=True,
    )
    risk_sorted = sorted(scenarios, key=lambda x: _risk_points(x.predicted_risk_class), reverse=True)
    feasibility_sorted = sorted(
        scenarios,
        key=lambda x: x.predicted_feasibility_score if x.predicted_feasibility_score is not None else -1,
        reverse=True,
    )
    confidence_sorted = sorted(
        scenarios,
        key=lambda x: _confidence_points(x.decision_confidence_score or x.prediction_confidence_score),
        reverse=True,
    )

    revenue_pos = {item.scenario_id: idx + 1 for idx, item in enumerate(revenue_sorted)}
    risk_pos = {item.scenario_id: idx + 1 for idx, item in enumerate(risk_sorted)}
    feasibility_pos = {item.scenario_id: idx + 1 for idx, item in enumerate(feasibility_sorted)}
    confidence_pos = {item.scenario_id: idx + 1 for idx, item in enumerate(confidence_sorted)}

    ranked_payload: List[Dict[str, Any]] = []
    for item in scenarios:
        overall_score = (
            0.34 * (item.predicted_feasibility_score or 50.0)
            + 0.26 * _revenue_points(item.predicted_monthly_net_revenue)
            + 0.22 * _risk_points(item.predicted_risk_class)
            + 0.18 * _confidence_points(item.decision_confidence_score or item.prediction_confidence_score)
        )
        ranked_payload.append({"item": item, "overall_score": round(overall_score, 2)})

    ranked_payload.sort(key=lambda x: x["overall_score"], reverse=True)

    rankings = [
        ScenarioComparisonItem(
            scenario_id=payload["item"].scenario_id,
            label=f"{payload['item'].business_subcategory} in {payload['item'].municipality_name} ({payload['item'].radius_km:g} km)",
            overall_score=payload["overall_score"],
            revenue_position=revenue_pos[payload["item"].scenario_id],
            risk_position=risk_pos[payload["item"].scenario_id],
            feasibility_position=feasibility_pos[payload["item"].scenario_id],
            confidence_position=confidence_pos[payload["item"].scenario_id],
            key_tradeoff=_tradeoff_text(payload["item"]),
        )
        for payload in ranked_payload
    ]

    best_id = rankings[0].scenario_id if rankings else None
    best_label = rankings[0].label if rankings else "No scenario"

    return ScenarioComparisonResponse(
        generated_at=generated_at,
        compared_count=len(rankings),
        best_overall_scenario_id=best_id,
        comparison_summary=(
            f"{best_label} currently ranks highest after balancing predicted feasibility, estimated revenue, risk class, and confidence. "
            "This comparison is a decision-support view, not a guaranteed investment outcome."
        ),
        rankings=rankings,
    )
