from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.competition import CompetitionObservationEvidence


class GeoCoordinate(BaseModel):
    latitude: float
    longitude: float


class MapMarker(BaseModel):
    marker_id: str
    marker_type: str
    label: str
    latitude: float
    longitude: float
    x_offset_pct: float
    y_offset_pct: float
    intensity: float
    source_method: str
    credibility: str
    osm_id: Optional[str] = None
    osm_type: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    address_source: Optional[str] = None
    tags: Dict[str, Any] = Field(default_factory=dict)


class HeatmapCell(BaseModel):
    cell_id: str
    latitude: float
    longitude: float
    demand_intensity: float
    risk_intensity: float
    label: str
    source_method: str




class FootfallHeatmapPoint(BaseModel):
    point_id: str
    latitude: float
    longitude: float
    intensity: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Relative display weight normalized from an observed pedestrian count.",
    )
    evidence_type: str
    source: str
    label: Optional[str] = None
    osm_id: Optional[str] = None
    category: Optional[str] = None
    observed_count: float = Field(ge=0)
    observed_unit: str
    observation_period: str
    source_url: Optional[str] = None


class DynamicOSMTagContext(BaseModel):
    key: str
    value: str
    confidence: float
    tag_role: str
    reason: Optional[str] = None


class BusinessResolutionMapContext(BaseModel):
    status: str
    input_text: str
    normalized_business_name: str = ""
    primary_category: str = ""
    secondary_categories: List[str] = Field(default_factory=list)
    brand_terms: List[str] = Field(default_factory=list)
    specialty_terms: List[str] = Field(default_factory=list)
    osm_tags: List[DynamicOSMTagContext] = Field(default_factory=list)
    resolution_confidence: str
    confidence_score: float
    source_method: str
    raw_ai_available: bool
    warnings: List[str] = Field(default_factory=list)
    raw_ai_error: Optional[str] = None


class GeospatialMarketRequest(BaseModel):
    municipality_name: str = Field(..., example="Kitchener")
    radius_km: float = Field(..., ge=1, le=25, example=5)
    site_address: Optional[str] = Field(
        default=None,
        description=(
            "Optional specific street address. When provided, the analysis radius and every "
            "OSM evidence layer are centred on this exact address instead of the municipality centre."
        ),
        example="100 King St W",
    )
    business_subcategory: Optional[str] = Field(
        default=None,
        description="Existing catalog-backed business subcategory. Kept for backward compatibility and current prediction/evidence flow.",
        example="Indian Grocery Store",
    )
    business_query: Optional[str] = Field(
        default=None,
        description="Free-text business idea. When supplied, Zonalyze resolves it with local AI and uses validated OSM tags for map evidence.",
        example="Esso gas station with Circle K convenience store",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional local Ollama model override for dynamic business resolution.",
    )

    @model_validator(mode="after")
    def require_business_input(self):
        if not (self.business_subcategory or self.business_query):
            raise ValueError("Provide either business_subcategory or business_query.")
        return self


class GeospatialMarketContext(BaseModel):
    municipality_name: str
    business_subcategory: str
    radius_km: float
    center: GeoCoordinate

    # Where the radius/evidence is anchored. "address" when a specific site_address
    # was geocoded successfully; "city_center" otherwise. resolved_address names the
    # exact geocoded site so the UI can be honest about the reference point.
    anchor_type: str = "city_center"
    resolved_address: Optional[str] = None
    geocode_confidence: Optional[str] = None
    municipality_match: Optional[bool] = None
    anchor_note: str = ""

    # How the feasibility score was derived for the requested business input.
    #   "exact_catalog"   -> user picked a trained catalog subcategory
    #   "nearest_catalog" -> free-text idea mapped to the closest trained type
    #   "unavailable"     -> no confident catalog match; map/competitors only
    score_basis: str = "exact_catalog"
    score_basis_subcategory: Optional[str] = None
    score_basis_note: str = ""

    map_method: str
    map_credibility: str
    coverage_note: str
    evidence_note: str
    radius_label: str
    competition_pressure_index: float
    demand_pressure_index: float
    rent_pressure_index: float
    marker_count: int
    real_competitor_count: int

    # Real OpenStreetMap-backed competition evidence for this radius (display /
    # decision only — never fed into the ML feature vector). Present when OSM was
    # live; null when it fell back to proxy/seed.
    competition_evidence: Optional[CompetitionObservationEvidence] = None
    competition_evidence_source: str = "proxy"
    transit_marker_count: int
    lease_marker_count: int
    markers: List[MapMarker]
    heatmap_cells: List[HeatmapCell]
    footfall_heatmap_points: List[FootfallHeatmapPoint] = Field(default_factory=list)
    footfall_heatmap_status: str = "not_requested"
    footfall_heatmap_note: str = "Observed pedestrian-counter heatmap was not built."
    footfall_heatmap_sources: List[str] = Field(default_factory=list)
    osm_query_status: str
    osm_query_note: str
    next_data_needed: List[str]

    # Step 27B dynamic business-resolution metadata.
    business_query: Optional[str] = None
    resolved_business_name: Optional[str] = None
    business_resolution: Optional[BusinessResolutionMapContext] = None
