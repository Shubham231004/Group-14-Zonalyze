from typing import Dict, List, Optional

from pydantic import BaseModel


class ModelFileStatus(BaseModel):
    risk_classifier: bool
    revenue_regressor: bool
    feasibility_regressor: bool
    metadata: bool


class ModelStatusResponse(BaseModel):
    status: str
    trained_at: Optional[str] = None
    dataset_path: Optional[str] = None
    row_count: int = 0
    feature_count: int = 0
    categorical_feature_count: int = 0
    numeric_feature_count: int = 0
    targets: Dict[str, str] = {}
    risk_accuracy: Optional[float] = None
    revenue_mae: Optional[float] = None
    revenue_rmse: Optional[float] = None
    revenue_r2: Optional[float] = None
    feasibility_mae: Optional[float] = None
    feasibility_rmse: Optional[float] = None
    feasibility_r2: Optional[float] = None
    model_files: ModelFileStatus
    important_note: str
