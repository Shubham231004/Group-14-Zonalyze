from pydantic import BaseModel, Field


class AnalyzeScenarioRequest(BaseModel):
    municipality_name: str = Field(..., example="Kitchener")
    business_subcategory: str = Field(..., example="Indian Grocery Store")
    radius_km: float = Field(..., ge=1, le=25, example=5)