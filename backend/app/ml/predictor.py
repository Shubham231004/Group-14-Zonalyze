from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = APP_DIR / "ml" / "models"

RISK_MODEL_PATH = MODELS_DIR / "risk_classifier.pkl"
REVENUE_MODEL_PATH = MODELS_DIR / "revenue_regressor.pkl"
FEASIBILITY_MODEL_PATH = MODELS_DIR / "feasibility_regressor.pkl"
METADATA_PATH = MODELS_DIR / "model_metadata.json"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.json"

_predictor_instance = None

RETRAIN_HINT = (
    "Run: python -m app.ml.train_models --rows 50000 --force-regenerate "
    "(from the backend folder) to build the model files locally."
)


class ModelsUnavailableError(RuntimeError):
    """Raised when trained model artifacts are missing or unreadable.

    This is handled centrally (see app/main.py) so the API returns a clear
    503 "models unavailable — retrain" message instead of a raw 500 stack trace.
    """


def models_available() -> tuple[bool, List[str]]:
    """Report whether all required model artifacts exist, without loading them."""
    required = {
        "risk_classifier.pkl": RISK_MODEL_PATH,
        "revenue_regressor.pkl": REVENUE_MODEL_PATH,
        "feasibility_regressor.pkl": FEASIBILITY_MODEL_PATH,
        "feature_columns.json": FEATURE_COLUMNS_PATH,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    return (len(missing) == 0, missing)


class ZonalyzePredictor:
    def __init__(self) -> None:
        self.metadata = self._load_metadata()
        self.feature_columns = self._load_feature_columns()
        self.categorical_columns = self._load_categorical_columns()
        self.numeric_columns = [
            col for col in self.feature_columns if col not in self.categorical_columns
        ]

        self.risk_model = self._load_model(RISK_MODEL_PATH, "risk classifier")
        self.revenue_model = self._load_model(REVENUE_MODEL_PATH, "revenue regressor")
        self.feasibility_model = self._load_model(
            FEASIBILITY_MODEL_PATH, "feasibility regressor"
        )

    def _load_metadata(self) -> Dict[str, Any]:
        if METADATA_PATH.exists():
            return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        return {
            "status": "metadata_missing",
            "important_note": (
                "Model metadata file is missing. Retrain models with "
                "python -m app.ml.train_models."
            ),
        }

    def _load_feature_columns(self) -> List[str]:
        if FEATURE_COLUMNS_PATH.exists():
            return json.loads(FEATURE_COLUMNS_PATH.read_text(encoding="utf-8"))

        columns = self.metadata.get("feature_columns")
        if isinstance(columns, list):
            return columns

        raise ModelsUnavailableError(
            f"Missing feature columns file: {FEATURE_COLUMNS_PATH}. {RETRAIN_HINT}"
        )

    def _load_categorical_columns(self) -> List[str]:
        metadata_categorical = self.metadata.get("categorical_columns")
        if isinstance(metadata_categorical, list):
            return [col for col in metadata_categorical if col in self.feature_columns]

        default_categorical = [
            "municipality_name",
            "business_subcategory",
            "business_group",
        ]
        return [col for col in default_categorical if col in self.feature_columns]

    def _load_model(self, path: Path, label: str):
        if not path.exists():
            raise ModelsUnavailableError(
                f"Missing {label} model file: {path}. {RETRAIN_HINT}"
            )
        try:
            return joblib.load(path)
        except Exception as exc:  # corrupted / incompatible artifact
            raise ModelsUnavailableError(
                f"Could not load {label} model file: {path} ({type(exc).__name__}: {exc}). {RETRAIN_HINT}"
            ) from exc

    def _clean_categorical_value(self, value: Any) -> str:
        if value is None:
            return "unknown"

        try:
            if pd.isna(value):
                return "unknown"
        except Exception:
            pass

        text = str(value).strip()

        if text == "" or text.lower() in {"nan", "none", "null"}:
            return "unknown"

        return text

    def _clean_numeric_value(self, value: Any) -> float:
        if value is None:
            return 0.0

        try:
            if pd.isna(value):
                return 0.0
        except Exception:
            pass

        if isinstance(value, (list, dict, tuple, set)):
            return 0.0

        cleaned = pd.to_numeric(value, errors="coerce")

        try:
            if pd.isna(cleaned):
                return 0.0
        except Exception:
            return 0.0

        cleaned_float = float(cleaned)

        if not np.isfinite(cleaned_float):
            return 0.0

        return cleaned_float

    def _feature_frame(self, features: Dict[str, Any]) -> pd.DataFrame:
        row: Dict[str, Any] = {}

        for column in self.feature_columns:
            raw_value = features.get(column)

            if column in self.categorical_columns:
                row[column] = self._clean_categorical_value(raw_value)
            else:
                row[column] = self._clean_numeric_value(raw_value)

        X = pd.DataFrame([row], columns=self.feature_columns)

        for column in self.categorical_columns:
            if column in X.columns:
                X[column] = X[column].astype(str).fillna("unknown")

        for column in self.numeric_columns:
            if column in X.columns:
                X[column] = (
                    pd.to_numeric(X[column], errors="coerce")
                    .replace([np.inf, -np.inf], np.nan)
                    .fillna(0.0)
                )

        return X

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        X = self._feature_frame(features)

        revenue = float(self.revenue_model.predict(X)[0])
        feasibility = float(self.feasibility_model.predict(X)[0])
        risk_class = str(self.risk_model.predict(X)[0])

        risk_probabilities: Dict[str, float] = {}

        if hasattr(self.risk_model, "predict_proba"):
            try:
                probabilities = self.risk_model.predict_proba(X)[0]
                classes = list(self.risk_model.classes_)
                risk_probabilities = {
                    str(cls): round(float(prob), 4)
                    for cls, prob in zip(classes, probabilities)
                }
            except Exception:
                risk_probabilities = {}

        recommendation = self._recommendation_from_outputs(
            revenue, feasibility, risk_class, risk_probabilities
        )

        return {
            "predicted_monthly_net_revenue": round(revenue, 2),
            "predicted_risk_class": risk_class,
            "risk_probabilities": risk_probabilities,
            "predicted_feasibility_score": round(max(0.0, min(100.0, feasibility)), 2),
            "recommendation": recommendation,
            "model_version": self.metadata.get("model_version", "unknown"),
        }

    def _recommendation_from_outputs(
        self,
        revenue: float,
        feasibility: float,
        risk_class: str,
        risk_probabilities: Dict[str, float],
    ) -> str:
        high_risk_prob = risk_probabilities.get("high", 0.0)
        low_risk_prob = risk_probabilities.get("low", 0.0)

        if (
            revenue > 4000
            and feasibility >= 68
            and risk_class == "low"
            and low_risk_prob >= 0.45
        ):
            return "recommended"

        if (
            revenue < -2500
            or feasibility < 42
            or risk_class == "high"
            or high_risk_prob >= 0.55
        ):
            return "not_recommended"

        return "borderline"


def get_predictor() -> ZonalyzePredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = ZonalyzePredictor()
    return _predictor_instance


def reset_predictor_cache() -> None:
    global _predictor_instance
    _predictor_instance = None