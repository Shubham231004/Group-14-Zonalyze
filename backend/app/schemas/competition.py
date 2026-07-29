from typing import List

from pydantic import BaseModel


class CompetitionObservationEvidence(BaseModel):
    municipality_name: str
    business_subcategory: str
    source_name: str
    source_method: str
    source_date: str
    method: str
    credibility: str
    observed_competitor_count: int
    competitor_density_per_10k: float
    nearest_competitor_distance_km: float | None = None
    avg_competitor_rating: float | None = None
    chain_share_pct: float | None = None
    competition_pressure_index: float
    data_quality_note: str


class CompetitionObservationCatalogResponse(BaseModel):
    count: int
    observations: List[CompetitionObservationEvidence]
