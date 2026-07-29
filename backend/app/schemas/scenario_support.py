from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ScenarioSupportRequest(BaseModel):
    municipality_name: str = Field(..., description="Selected municipality name.")
    business_subcategory: str = Field(..., description="Selected catalog-backed business subcategory used by the ML model.")
    radius_km: float = Field(..., ge=1, le=25, description="Selected search radius in kilometres.")
    business_input_mode: str = Field(default="catalog", description="catalog or custom")
    custom_business_query: Optional[str] = Field(default=None, description="Free-text custom business idea, if custom mode is active.")
    use_custom_business_for_map: bool = Field(default=False, description="Whether the user enabled the resolved custom business for map evidence.")
    business_resolution_status: Optional[str] = Field(default=None, description="Latest /business/resolve status, if available.")
    resolved_osm_tag_count: int = Field(default=0, ge=0, description="Count of validated OSM tags returned by the resolver.")
    business_resolution_confidence: Optional[str] = Field(default=None, description="Resolver confidence label, if available.")


class ScenarioSupportSection(BaseModel):
    status: str
    label: str
    summary: str
    reasons: List[str] = Field(default_factory=list)
    required_next_steps: List[str] = Field(default_factory=list)


class ScenarioSupportResponse(BaseModel):
    overall_status: str
    overall_label: str
    summary: str
    prediction_support: ScenarioSupportSection
    map_evidence_support: ScenarioSupportSection
    data_trust_notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    allowed_next_actions: List[str] = Field(default_factory=list)
