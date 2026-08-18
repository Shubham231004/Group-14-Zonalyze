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
    # The 0-100 score the recommendation label is derived from. It used to live only
    # inside decision_summary prose, so the comparison table had to invent its own —
    # and the two disagreed. Exposed so every surface shows this one number.
    decision_score: float
    decision_confidence_score: float
    confidence_level: str
    decision_summary: str
    decision_rationale: str
    action_guidance: str
    major_strengths: List[str]
    major_concerns: List[str]
    evidence_signals: List[RecommendationEvidenceSignal]
    caution_note: str
