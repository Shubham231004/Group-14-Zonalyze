import json
from pathlib import Path
from typing import Any, Dict

from app.schemas.model_status import ModelFileStatus, ModelStatusResponse


APP_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = APP_DIR / "ml" / "models"

METADATA_PATH = MODEL_DIR / "model_metadata.json"
RISK_MODEL_PATH = MODEL_DIR / "risk_classifier.pkl"
REVENUE_MODEL_PATH = MODEL_DIR / "revenue_regressor.pkl"
FEASIBILITY_MODEL_PATH = MODEL_DIR / "feasibility_regressor.pkl"
FEATURE_COLUMNS_PATH = MODEL_DIR / "feature_columns.json"


def _load_metadata() -> Dict[str, Any]:
    if not METADATA_PATH.exists():
        return {}

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_model_status() -> ModelStatusResponse:
    metadata = _load_metadata()

    file_status = ModelFileStatus(
        risk_classifier=RISK_MODEL_PATH.exists(),
        revenue_regressor=REVENUE_MODEL_PATH.exists(),
        feasibility_regressor=FEASIBILITY_MODEL_PATH.exists(),
        metadata=METADATA_PATH.exists(),
    )

    all_files_ready = all(
        [
            file_status.risk_classifier,
            file_status.revenue_regressor,
            file_status.feasibility_regressor,
            file_status.metadata,
        ]
    )

    categorical_features = metadata.get("categorical_features", []) or []
    feature_count = int(metadata.get("feature_count", 0) or 0)
    numeric_feature_count = max(0, feature_count - len(categorical_features))

    return ModelStatusResponse(
        status="ready" if all_files_ready else "incomplete",
        trained_at=metadata.get("trained_at_utc") or metadata.get("trained_at"),
        dataset_path=metadata.get("dataset_path"),
        row_count=int(metadata.get("row_count", 0) or 0),
        feature_count=feature_count,
        categorical_feature_count=len(categorical_features),
        numeric_feature_count=numeric_feature_count,
        targets={
            "revenue": "monthly_net_revenue",
            "risk": "risk_class",
            "feasibility": "feasibility_score",
        },
        risk_accuracy=metadata.get("risk_accuracy"),
        revenue_mae=metadata.get("revenue_mae"),
        revenue_rmse=None,
        revenue_r2=metadata.get("revenue_r2"),
        feasibility_mae=metadata.get("feasibility_mae"),
        feasibility_rmse=None,
        feasibility_r2=metadata.get("feasibility_r2"),
        model_files=file_status,
        important_note=(
            "Model files are missing or incomplete. Run "
            "`python -m app.ml.train_models --rows 50000 --force-regenerate` from the "
            "backend folder to build them locally (the .pkl files are gitignored)."
            if not all_files_ready
            else metadata.get(
                "important_note",
                "Models are trained on simulation-generated proxy labels. Use them for scenario comparison only until real commercial outcome data is integrated.",
            )
        ),
    )