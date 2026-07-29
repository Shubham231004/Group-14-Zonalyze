from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class OperatingProfileRequest(BaseModel):
    municipality_name: str = Field(..., example="Kitchener")
    radius_km: float = Field(default=5, ge=1, le=25, example=5)
    business_query: Optional[str] = Field(
        default=None,
        description="Free-text business idea from the user, for example 'Esso gas station with Circle K convenience store'.",
    )
    business_subcategory: Optional[str] = Field(
        default=None,
        description="Known catalog business subcategory used by the existing ML model, if available.",
    )
    business_resolution: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional /business/resolve response object already available on the frontend/backend.",
    )
    model: Optional[str] = Field(default=None, description="Optional local Ollama model override.")

    @model_validator(mode="after")
    def require_business_context(self):
        if not (self.business_query or self.business_subcategory):
            raise ValueError("Provide either business_query or business_subcategory.")
        return self


class OperatingProfileRange(BaseModel):
    low: Optional[float] = None
    median: Optional[float] = None
    high: Optional[float] = None
    unit: str = ""
    display_value: str = ""


class OperatingProfileSection(BaseModel):
    key: str
    title: str
    status: str = Field(
        description="estimated, evidence_supported, limited_estimate, needs_review, or unavailable"
    )
    estimate_type: str = Field(
        description="ai_benchmark_estimate, evidence_assisted_ai_estimate, observed_evidence, or unavailable"
    )
    confidence: str = Field(description="limited, moderate, high, or unavailable")
    range: Optional[OperatingProfileRange] = None
    summary: str
    reasoning: List[str] = Field(default_factory=list)
    evidence_used: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class OperatingProfileResponse(BaseModel):
    status: str
    municipality_name: str
    business_query: Optional[str] = None
    business_subcategory: Optional[str] = None
    normalized_business_name: Optional[str] = None
    radius_km: float
    source_method: str
    cache_status: str = "not_used"
    model: Optional[str] = None
    overall_confidence: str
    user_facing_note: str
    sections: List[OperatingProfileSection]
    warnings: List[str] = Field(default_factory=list)
    next_data_needed: List[str] = Field(default_factory=list)
    raw_ai_available: bool = False
    raw_ai_error: Optional[str] = None
