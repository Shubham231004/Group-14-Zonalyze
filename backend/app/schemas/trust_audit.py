from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrustAuditItem(BaseModel):
    field_name: str
    display_name: str
    current_location: str
    output_category: str = Field(
        description="observed_data, model_prediction, proxy_estimate, derived_metric, heuristic_formula, catalog_assumption, user_input, fallback"
    )
    current_method: str
    trust_level: str = Field(description="high, medium, limited, weak, unacceptable")
    user_facing_risk: str = Field(description="low, medium, high")
    issue: Optional[str] = None
    recommended_action: str
    replacement_priority: str = Field(description="keep, label, recalibrate, replace, remove")
    suggested_source_or_fix: Optional[str] = None


class TrustAuditSummary(BaseModel):
    total_items: int
    high_risk_items: int
    weak_or_unacceptable_items: int
    items_requiring_replacement: int
    items_requiring_relabeling: int
    overall_status: str
    summary_message: str


class TrustAuditResponse(BaseModel):
    audit_version: str
    project_phase: str
    summary: TrustAuditSummary
    categories: Dict[str, int]
    items: List[TrustAuditItem]
    immediate_cleanup_order: List[str]
    implementation_notes: List[str]
