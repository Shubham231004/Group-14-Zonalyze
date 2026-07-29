"""
Step 18 - Train Zonalyze ML models from the improved generated dataset.

Run from the backend folder:
    python -m app.ml.train_models --rows 50000

Outputs are written to:
    app/ml/models/risk_classifier.pkl
    app/ml/models/revenue_regressor.pkl
    app/ml/models/feasibility_regressor.pkl
    app/ml/models/model_metadata.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ml.generate_training_dataset import DEFAULT_OUTPUT_PATH, generate_dataset

APP_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = APP_DIR / "ml" / "models"
RISK_MODEL_PATH = MODELS_DIR / "risk_classifier.pkl"
REVENUE_MODEL_PATH = MODELS_DIR / "revenue_regressor.pkl"
FEASIBILITY_MODEL_PATH = MODELS_DIR / "feasibility_regressor.pkl"
METADATA_PATH = MODELS_DIR / "model_metadata.json"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.json"

TARGET_COLUMNS = ["monthly_net_revenue", "risk_class", "feasibility_score", "risk_score"]
CATEGORICAL_FEATURES = ["municipality_name", "business_subcategory", "business_group"]


def _feature_columns(df: pd.DataFrame) -> List[str]:
    excluded = set(TARGET_COLUMNS)
    return [col for col in df.columns if col not in excluded]


def _build_preprocessor(feature_columns: List[str]) -> ColumnTransformer:
    categorical = [col for col in CATEGORICAL_FEATURES if col in feature_columns]
    numeric = [col for col in feature_columns if col not in categorical]
    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("numeric", StandardScaler(), numeric),
        ],
        remainder="drop",
    )


def _load_or_generate_dataset(rows: int, dataset_path: Path, force_regenerate: bool) -> pd.DataFrame:
    if force_regenerate or not dataset_path.exists():
        return generate_dataset(rows=rows, output_path=dataset_path)
    return pd.read_csv(dataset_path)


def train_models(rows: int = 50000, dataset_path: Path = DEFAULT_OUTPUT_PATH, force_regenerate: bool = False) -> dict:
    df = _load_or_generate_dataset(rows=rows, dataset_path=dataset_path, force_regenerate=force_regenerate)
    if df.empty:
        raise RuntimeError("Training dataset is empty.")

    feature_columns = _feature_columns(df)
    X = df[feature_columns]
    y_revenue = df["monthly_net_revenue"]
    y_risk = df["risk_class"]
    y_feasibility = df["feasibility_score"]

    print("Risk class distribution:")
    print(y_risk.value_counts())

    risk_class_counts = y_risk.value_counts()
    if not risk_class_counts.empty and risk_class_counts.min() >= 2:
        stratify_target = y_risk
    else:
        stratify_target = None
        print(
            "Warning: Risk class distribution is too imbalanced for stratified split. "
            f"Class counts: {risk_class_counts.to_dict()}. "
            "Training will continue without stratification."
        )

    X_train, X_test, y_rev_train, y_rev_test, y_risk_train, y_risk_test, y_feas_train, y_feas_test = train_test_split(
        X,
        y_revenue,
        y_risk,
        y_feasibility,
        test_size=0.20,
        random_state=42,
        stratify=stratify_target,
    )

    revenue_model = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor(feature_columns)),
            ("model", RandomForestRegressor(n_estimators=180, random_state=42, n_jobs=-1, min_samples_leaf=3)),
        ]
    )
    feasibility_model = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor(feature_columns)),
            ("model", RandomForestRegressor(n_estimators=180, random_state=42, n_jobs=-1, min_samples_leaf=3)),
        ]
    )
    risk_model = Pipeline(
        steps=[
            ("preprocessor", _build_preprocessor(feature_columns)),
            ("model", RandomForestClassifier(n_estimators=220, random_state=42, n_jobs=-1, class_weight="balanced", min_samples_leaf=3)),
        ]
    )

    print("Training revenue regressor...")
    revenue_model.fit(X_train, y_rev_train)
    print("Training feasibility regressor...")
    feasibility_model.fit(X_train, y_feas_train)
    print("Training risk classifier...")
    risk_model.fit(X_train, y_risk_train)

    rev_pred = revenue_model.predict(X_test)
    feas_pred = feasibility_model.predict(X_test)
    risk_pred = risk_model.predict(X_test)

    metadata = {
        "model_version": "step18_business_catalog_v2",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(dataset_path),
        "row_count": int(len(df)),
        "feature_count": int(len(feature_columns)),
        "feature_columns": feature_columns,
        "categorical_features": [col for col in CATEGORICAL_FEATURES if col in feature_columns],
        "target_columns": TARGET_COLUMNS,
        "municipality_count": int(df["municipality_name"].nunique()) if "municipality_name" in df else None,
        "business_subcategory_count": int(df["business_subcategory"].nunique()) if "business_subcategory" in df else None,
        "risk_accuracy": round(float(accuracy_score(y_risk_test, risk_pred)), 4),
        "risk_classification_report": classification_report(y_risk_test, risk_pred, output_dict=True),
        "revenue_r2": round(float(r2_score(y_rev_test, rev_pred)), 4),
        "revenue_mae": round(float(mean_absolute_error(y_rev_test, rev_pred)), 2),
        "feasibility_r2": round(float(r2_score(y_feas_test, feas_pred)), 4),
        "feasibility_mae": round(float(mean_absolute_error(y_feas_test, feas_pred)), 2),
        "important_note": "Models are trained on improved simulation-generated labels. They support prototype predictions and should not be presented as validated real-world financial outcomes.",
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(risk_model, RISK_MODEL_PATH)
    joblib.dump(revenue_model, REVENUE_MODEL_PATH)
    joblib.dump(feasibility_model, FEASIBILITY_MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    FEATURE_COLUMNS_PATH.write_text(json.dumps(feature_columns, indent=2), encoding="utf-8")

    print("Saved models to:")
    print(f"  {RISK_MODEL_PATH}")
    print(f"  {REVENUE_MODEL_PATH}")
    print(f"  {FEASIBILITY_MODEL_PATH}")
    print(f"  {METADATA_PATH}")
    print(json.dumps({
        "risk_accuracy": metadata["risk_accuracy"],
        "revenue_r2": metadata["revenue_r2"],
        "feasibility_r2": metadata["feasibility_r2"],
        "row_count": metadata["row_count"],
        "feature_count": metadata["feature_count"],
    }, indent=2))
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Zonalyze Step 18 ML models.")
    parser.add_argument("--rows", type=int, default=50000, help="Rows to generate if dataset does not exist.")
    parser.add_argument("--dataset", type=str, default=str(DEFAULT_OUTPUT_PATH), help="Dataset CSV path.")
    parser.add_argument("--force-regenerate", action="store_true", help="Regenerate dataset before training.")
    args = parser.parse_args()
    train_models(rows=args.rows, dataset_path=Path(args.dataset), force_regenerate=args.force_regenerate)


if __name__ == "__main__":
    main()
