from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class SiteAddressAnalysisRequest(BaseModel):
    address_line: str = Field(..., min_length=3, example="100 King St W")
    municipality_name: str = Field(..., example="Kitchener")
    radius_km: float = Field(default=1.5, ge=0.25, le=10, example=1.5)
    business_subcategory: Optional[str] = Field(default=None, example="Indian Grocery Store")
    business_query: Optional[str] = Field(default=None, example="Esso gas station with Circle K convenience store")

    @model_validator(mode="after")
    def clean_values(self):
        self.address_line = " ".join(str(self.address_line or "").split())
        self.municipality_name = " ".join(str(self.municipality_name or "").split())
        if self.business_subcategory:
            self.business_subcategory = " ".join(str(self.business_subcategory).split())
        if self.business_query:
            self.business_query = " ".join(str(self.business_query).split())
        return self


class SiteCoordinate(BaseModel):
    latitude: float
    longitude: float


class SiteGeocodeCandidate(BaseModel):
    display_name: str
    latitude: float
    longitude: float
    resolved_municipality: Optional[str] = None
    municipality_match: bool = False
    confidence: str = "limited"
    importance: Optional[float] = None
    source: str = "OpenStreetMap Nominatim"


class SiteEvidenceItem(BaseModel):
    name: str
    category: str
    distance_km: float
    latitude: float
    longitude: float
    address: Optional[str] = None
    source: str = "OpenStreetMap"


class SiteEvidenceSummary(BaseModel):
    count: int
    nearest: Optional[SiteEvidenceItem] = None
    items: List[SiteEvidenceItem] = Field(default_factory=list)
    status: str = Field(
        default="unknown",
        description="available, no_results, query_failed, skipped, or unknown",
    )
    note: Optional[str] = None


class SiteAddressAnalysisResponse(BaseModel):
    status: str
    input_address: str
    resolved_address: Optional[str] = None
    resolved_municipality: Optional[str] = None
    municipality_name: str
    municipality_match: bool = False
    radius_km: float
    coordinate: Optional[SiteCoordinate] = None
    geocode_source: str
    geocode_confidence: str
    geocode_candidates: List[SiteGeocodeCandidate] = Field(default_factory=list)
    competitor_evidence: SiteEvidenceSummary
    transit_evidence: SiteEvidenceSummary
    commercial_activity_evidence: SiteEvidenceSummary
    source_method: str
    user_facing_note: str
    warnings: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
