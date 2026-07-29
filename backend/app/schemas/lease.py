from pydantic import BaseModel


class LeaseCostEvidence(BaseModel):
    municipality_name: str
    business_subcategory: str
    source_name: str
    source_method: str
    source_date: str
    method: str
    credibility: str
    estimated_space_sqft: float
    low_monthly_lease_cost: float
    median_monthly_lease_cost: float
    high_monthly_lease_cost: float
    lease_cost_per_sqft_year: float
    rent_pressure_index: float
    commercial_cost_pressure_level: str
    data_quality_note: str


class LeaseCostCatalogResponse(BaseModel):
    count: int
    observations: list[LeaseCostEvidence]
