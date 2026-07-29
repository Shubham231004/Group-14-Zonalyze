from pydantic import BaseModel


class DemandEvidence(BaseModel):
    municipality_name: str
    business_subcategory: str
    source_name: str
    source_method: str
    source_date: str
    method: str
    credibility: str
    reachable_population_estimate: float
    target_customer_pool_estimate: float
    daytime_activity_index: float
    foot_traffic_proxy_index: float
    transit_access_proxy_index: float
    demographic_fit_score: float
    demand_pressure_index: float
    demand_level: str
    data_quality_note: str


class DemandEvidenceCatalogResponse(BaseModel):
    count: int
    observations: list[DemandEvidence]
