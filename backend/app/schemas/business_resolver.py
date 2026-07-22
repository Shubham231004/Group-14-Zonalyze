from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BusinessResolveRequest(BaseModel):
    business_query: str = Field(
        ...,
        min_length=2,
        description="Free-text business idea entered by the user. Example: Michelin tyre shop.",
    )
    municipality_name: Optional[str] = Field(
        default=None,
        description="Optional location context. Reserved for future coverage scoring.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional local Ollama model override.",
    )


class OSMTagSuggestion(BaseModel):
    key: str
    value: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    tag_role: str = Field(default="primary")
    reason: Optional[str] = None


class BusinessResolveResponse(BaseModel):
    status: str = Field(description="resolved, needs_review, or failed")
    input_text: str
    normalized_business_name: str = ""
    primary_category: str = ""
    secondary_categories: List[str] = Field(default_factory=list)
    brand_terms: List[str] = Field(default_factory=list)
    specialty_terms: List[str] = Field(default_factory=list)
    osm_tags: List[OSMTagSuggestion] = Field(default_factory=list)
    rejected_osm_tags: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_confidence: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_method: str
    raw_ai_available: bool
    warnings: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    raw_ai_error: Optional[str] = None

    # Nearest trained catalog subcategory for feasibility scoring. Lets the frontend
    # request an ML score for a free-text idea while being honest that the score is
    # based on the closest known business type. None when nothing matched.
    nearest_catalog_subcategory: Optional[str] = None
    nearest_catalog_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    score_basis: str = "unavailable"
    score_basis_note: str = ""
