from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FeatureAlignmentIssue(BaseModel):
    severity: str
    message: str


class FeatureAlignmentPredictionTest(BaseModel):
    status: str
    prediction: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class FeatureAlignmentResponse(BaseModel):
    status: str
    municipality_name: str
    business_subcategory: str
    radius_km: float

    model_version: str = "unknown"
    model_feature_count: int = 0
    runtime_feature_count: int = 0
    cleaned_feature_count: int = 0

    missing_runtime_features: List[str] = []
    extra_runtime_features: List[str] = []
    categorical_features: List[str] = []
    numeric_features: List[str] = []

    categorical_values: Dict[str, str] = {}
    raw_feature_type_summary: Dict[str, str] = {}
    numeric_health: Dict[str, Any] = {}
    model_files: Dict[str, bool] = {}

    prediction_test: FeatureAlignmentPredictionTest
    issues: List[FeatureAlignmentIssue] = []
    recommendation: str
