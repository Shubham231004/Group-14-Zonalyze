from typing import List

from pydantic import BaseModel


class RecommendationEvidenceSignal(BaseModel):
    name: str
    value: str
    direction: str
    impact: str
    source_type: str


class RecommendationDecision(BaseModel):
    final_recommendation: str
    recommendation_label: str
    decision_confidence_score: float
    confidence_level: str
    decision_summary: str
    decision_rationale: str
    action_guidance: str
    major_strengths: List[str]
    major_concerns: List[str]
    evidence_signals: List[RecommendationEvidenceSignal]
    caution_note: str
