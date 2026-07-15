from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from app.ml.predictor import (
    FEASIBILITY_MODEL_PATH,
    FEATURE_COLUMNS_PATH,
    METADATA_PATH,
    REVENUE_MODEL_PATH,
    RISK_MODEL_PATH,
    get_predictor,
)
from app.ml.scenario_feature_builder import build_prediction_features
from app.schemas.feature_alignment import (
    FeatureAlignmentIssue,
    FeatureAlignmentPredictionTest,
    FeatureAlignmentResponse,
)
from app.schemas.scenario import AnalyzeScenarioRequest


DEFAULT_MUNICIPALITY = "Kitchener"
DEFAULT_BUSINESS_SUBCATEGORY = "Indian Grocery Store"
DEFAULT_RADIUS_KM = 5


def _build_runtime_features(request: AnalyzeScenarioRequest) -> Dict[str, Any]:
    """Build the same feature row used by dashboard prediction.

    This mirrors dashboard_service.analyze_scenario: the model is scored on the
    clean, training-consistent feature row from the shared pipeline. Evidence
    services are display-only and are intentionally not applied here.
    """
    features = build_prediction_features(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )
    features["municipality_name"] = request.municipality_name
    return features


def _type_name(value: Any) -> str:
    if value is None:
        return "None"
    return type(value).__name__


def _is_bad_numeric(value: Any) -> bool:
    try:
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric):
            return True
        return not bool(np.isfinite(float(numeric)))
    except Exception:
        return True


def _numeric_health_from_frame(X: pd.DataFrame, numeric_columns: List[str]) -> Dict[str, Any]:
    if not numeric_columns:
        return {
            "numeric_column_count": 0,
            "null_count_after_cleaning": 0,
            "infinite_count_after_cleaning": 0,
            "columns_with_remaining_nulls": [],
        }

    numeric = X[numeric_columns].apply(pd.to_numeric, errors="coerce")
    null_counts = numeric.isna().sum()
    inf_counts = np.isinf(numeric.to_numpy(dtype=float, copy=True)).sum()

    columns_with_nulls = [col for col, count in null_counts.items() if int(count) > 0]

    return {
        "numeric_column_count": len(numeric_columns),
        "null_count_after_cleaning": int(null_counts.sum()),
        "infinite_count_after_cleaning": int(inf_counts),
        "columns_with_remaining_nulls": columns_with_nulls,
        "sample_min_max": {
            col: {
                "value": float(numeric[col].iloc[0]) if len(numeric[col]) else 0.0,
            }
            for col in numeric_columns[:15]
        },
    }


def _model_file_status() -> Dict[str, bool]:
    return {
        "risk_classifier": RISK_MODEL_PATH.exists(),
        "revenue_regressor": REVENUE_MODEL_PATH.exists(),
        "feasibility_regressor": FEASIBILITY_MODEL_PATH.exists(),
        "metadata": METADATA_PATH.exists(),
        "feature_columns": FEATURE_COLUMNS_PATH.exists(),
    }


def run_feature_alignment(
    request: AnalyzeScenarioRequest | None = None,
) -> FeatureAlignmentResponse:
    if request is None:
        request = AnalyzeScenarioRequest(
            municipality_name=DEFAULT_MUNICIPALITY,
            business_subcategory=DEFAULT_BUSINESS_SUBCATEGORY,
            radius_km=DEFAULT_RADIUS_KM,
        )

    issues: List[FeatureAlignmentIssue] = []

    try:
        predictor = get_predictor()
    except Exception as exc:
        return FeatureAlignmentResponse(
            status="failed",
            municipality_name=request.municipality_name,
            business_subcategory=request.business_subcategory,
            radius_km=request.radius_km,
            model_files=_model_file_status(),
            prediction_test=FeatureAlignmentPredictionTest(status="failed", error=str(exc)),
            issues=[
                FeatureAlignmentIssue(
                    severity="error",
                    message=f"Predictor could not be initialized: {exc}",
                )
            ],
            recommendation="Fix model files first. Run python -m app.ml.train_models --rows 50000 --force-regenerate and confirm backend/app/ml/models contains the .pkl files plus feature_columns.json.",
        )

    try:
        runtime_features = _build_runtime_features(request)
    except Exception as exc:
        return FeatureAlignmentResponse(
            status="failed",
            municipality_name=request.municipality_name,
            business_subcategory=request.business_subcategory,
            radius_km=request.radius_km,
            model_version=predictor.metadata.get("model_version", "unknown"),
            model_feature_count=len(predictor.feature_columns),
            model_files=_model_file_status(),
            prediction_test=FeatureAlignmentPredictionTest(status="failed", error=str(exc)),
            issues=[
                FeatureAlignmentIssue(
                    severity="error",
                    message=f"Runtime feature builder failed: {exc}",
                )
            ],
            recommendation="Fix build_prediction_features() or the selected municipality/business catalog before testing the model.",
        )

    model_features = list(predictor.feature_columns)
    runtime_keys = sorted(runtime_features.keys())
    missing = [col for col in model_features if col not in runtime_features]
    extra = [col for col in runtime_keys if col not in model_features]

    if missing:
        issues.append(
            FeatureAlignmentIssue(
                severity="warning",
                message=(
                    f"{len(missing)} model feature(s) are not directly produced by runtime feature builder. "
                    "Predictor will fill these with safe defaults, but prediction quality may be weaker."
                ),
            )
        )

    if extra:
        issues.append(
            FeatureAlignmentIssue(
                severity="info",
                message=(
                    f"{len(extra)} extra runtime feature(s) are produced but not used by the trained model. "
                    "This is acceptable if they are explanation/evidence fields."
                ),
            )
        )

    try:
        X = predictor._feature_frame(runtime_features)
        cleaned_feature_count = int(len(X.columns))
        numeric_health = _numeric_health_from_frame(X, predictor.numeric_columns)
        categorical_values = {
            col: str(X[col].iloc[0])
            for col in predictor.categorical_columns
            if col in X.columns
        }
    except Exception as exc:
        return FeatureAlignmentResponse(
            status="failed",
            municipality_name=request.municipality_name,
            business_subcategory=request.business_subcategory,
            radius_km=request.radius_km,
            model_version=predictor.metadata.get("model_version", "unknown"),
            model_feature_count=len(model_features),
            runtime_feature_count=len(runtime_features),
            missing_runtime_features=missing,
            extra_runtime_features=extra,
            categorical_features=predictor.categorical_columns,
            numeric_features=predictor.numeric_columns,
            raw_feature_type_summary={key: _type_name(value) for key, value in runtime_features.items()},
            model_files=_model_file_status(),
            prediction_test=FeatureAlignmentPredictionTest(status="failed", error=str(exc)),
            issues=issues
            + [
                FeatureAlignmentIssue(
                    severity="error",
                    message=f"Predictor feature-frame cleaning failed: {exc}",
                )
            ],
            recommendation="Fix predictor._feature_frame() cleaning logic or model feature_columns.json.",
        )

    prediction_test: FeatureAlignmentPredictionTest
    try:
        prediction = predictor.predict(runtime_features)
        prediction_test = FeatureAlignmentPredictionTest(status="passed", prediction=prediction)
    except Exception as exc:
        prediction_test = FeatureAlignmentPredictionTest(status="failed", error=str(exc))
        issues.append(
            FeatureAlignmentIssue(
                severity="error",
                message=f"Live prediction failed: {exc}",
            )
        )

    if prediction_test.status == "failed":
        status = "failed"
    elif missing:
        status = "warning"
    else:
        status = "passed"

    if status == "passed":
        recommendation = "Feature alignment passed. Runtime feature generation, model feature columns, cleaning, and prediction execution are compatible."
    elif status == "warning":
        recommendation = "Prediction works, but runtime features do not perfectly match model features. Review missing_runtime_features before final demo."
    else:
        recommendation = "Prediction alignment failed. Fix the reported errors before relying on dashboard predictions."

    return FeatureAlignmentResponse(
        status=status,
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
        model_version=predictor.metadata.get("model_version", "unknown"),
        model_feature_count=len(model_features),
        runtime_feature_count=len(runtime_features),
        cleaned_feature_count=cleaned_feature_count,
        missing_runtime_features=missing,
        extra_runtime_features=extra,
        categorical_features=predictor.categorical_columns,
        numeric_features=predictor.numeric_columns,
        categorical_values=categorical_values,
        raw_feature_type_summary={key: _type_name(value) for key, value in runtime_features.items()},
        numeric_health=numeric_health,
        model_files=_model_file_status(),
        prediction_test=prediction_test,
        issues=issues,
        recommendation=recommendation,
    )
