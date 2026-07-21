from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.ai_assistant import ScenarioChatRequest, ScenarioChatResponse
from app.schemas.scenario import AnalyzeScenarioRequest
from app.services.ai_context_service import (
    build_limitations,
    build_prompt,
    build_scenario_snapshot,
    build_used_signals,
    fallback_answer,
)
from app.services.dashboard_service import analyze_scenario
from app.services.local_ai_service import generate_with_ollama, resolve_model


MAX_HISTORY_MESSAGES = 6


def _history_to_text(request: ScenarioChatRequest) -> str:
    if not request.chat_history:
        return ""

    messages = request.chat_history[-MAX_HISTORY_MESSAGES:]
    lines = []
    for message in messages:
        role = message.role.strip().lower()
        if role not in {"user", "assistant"}:
            role = "user"
        content = message.content.strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _follow_up_suggestions(recommendation: str | None) -> list[str]:
    common = [
        "What is the biggest risk in this scenario?",
        "What can I change to improve feasibility?",
        "Which values are real data and which are estimates?",
        "How reliable is this prediction?",
    ]
    if recommendation == "not_recommended":
        return [
            "What would need to change for this to become viable?",
            "Would a smaller store size or lower rent help?",
            *common[:2],
        ]
    if recommendation == "recommended":
        return [
            "What should I verify before investing?",
            "What could make this scenario fail?",
            *common[2:],
        ]
    return common


def answer_scenario_question(request: ScenarioChatRequest, db: Session) -> ScenarioChatResponse:
    dashboard = analyze_scenario(
        request=AnalyzeScenarioRequest(
            municipality_name=request.municipality_name,
            business_subcategory=request.business_subcategory,
            radius_km=request.radius_km,
        ),
        db=db,
    )

    snapshot = build_scenario_snapshot(dashboard)
    used_signals = build_used_signals(snapshot)
    limitations = build_limitations(snapshot)
    prompt = build_prompt(
        snapshot=snapshot,
        question=request.question,
        chat_history_text=_history_to_text(request),
    )

    # Constrain the model to the server allowlist so a client cannot force an
    # arbitrary Ollama model to be pulled/run.
    ai_result = generate_with_ollama(prompt=prompt, model=resolve_model(request.model))

    if ai_result.available:
        answer = ai_result.answer
        status = "answered"
        error = None
    else:
        answer = fallback_answer(snapshot, request.question)
        status = "fallback_answered"
        error = ai_result.error

    recommendation = snapshot.get("recommendation_decision", {}).get("final_recommendation")

    return ScenarioChatResponse(
        status=status,
        answer=answer,
        model=ai_result.model,
        ai_provider="ollama_local",
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        used_signals=used_signals,
        limitations=limitations,
        follow_up_suggestions=_follow_up_suggestions(recommendation),
        scenario_snapshot=snapshot,
        raw_ai_available=ai_result.available,
        error=error,
    )
