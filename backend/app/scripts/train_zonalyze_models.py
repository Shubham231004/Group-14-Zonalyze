"""
Zonalyze - ML Training Pipeline

Purpose:
    Trains machine learning models using the synthetic scenario dataset created
    from real Ontario census features + controlled business scenario formulas.

Input:
    app/data/synthetic/zonalyze_synthetic_scenarios_2021.csv

Outputs:
    app/ml/models/risk_classifier.pkl
    app/ml/models/revenue_regressor.pkl
    app/ml/models/feasibility_regressor.pkl
    app/ml/models/model_metadata.json
    app/ml/reports/training_report.txt

Run from backend/:
    python app/scripts/train_zonalyze_models.py

Recommended install:
    pip install pandas scikit-learn joblib
"""

from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DATA_PATH = Path("app/data/synthetic/zonalyze_synthetic_scenarios_2021.csv")
MODEL_DIR = Path("app/ml/models")
REPORT_DIR = Path("app/ml/reports")

RANDOM_STATE = 42
TEST_SIZE = 0.2


CATEGORICAL_FEATURES = [
    "municipality_type",
    "business_category",
    "business_subcategory",
]

NUMERIC_FEATURES = [
    # Scenario inputs
    "radius_km",

    # Real census features
    "population_2021",
    "population_density_per_km2",
    "population_growth_2016_2021_pct",
    "household_median_total_income_2020",
    "children_0_14_pct",
    "youth_15_24_pct",
    "young_adult_20_34_pct",
    "working_age_25_64_pct",
    "seniors_65_plus_pct",
    "family_with_children_pct",
    "employment_rate_pct",
    "unemployment_rate_pct",
    "immigrant_pct",
    "visible_minority_pct",
    "diversity_index_0_100",
    "renter_pct",
    "renter_average_monthly_shelter_cost",
    "rent_pressure_index_0_100",
    "market_base_index_0_100",

    # Business assumptions and generated scenario inputs
    "average_ticket_size",
    "base_capture_rate",
    "gross_margin_pct",
    "estimated_space_sqft",
    "reachable_population_estimate",
    "demographic_fit_score_0_100",
    "demand_score_0_100",
    "competitor_count_estimate",
    "competitor_density_per_10k",
    "competition_score_0_100",
    "monthly_lease_cost_estimate",
    "monthly_staff_cost_estimate",
    "monthly_utilities_cost_estimate",
    "monthly_marketing_cost_estimate",
    "monthly_operating_cost_estimate",
]

FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES

RISK_TARGET = "investment_risk_class"
REVENUE_TARGET = "monthly_net_revenue_estimate"
FEASIBILITY_TARGET = "feasibility_score_0_100"


def ensure_paths() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}\n"
            "Run generate_synthetic_scenarios.py first."
        )

    df = pd.read_csv(DATA_PATH)
    return df


def validate_dataset(df: pd.DataFrame) -> None:
    required = FEATURE_COLUMNS + [RISK_TARGET, REVENUE_TARGET, FEASIBILITY_TARGET]
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df.empty:
        raise ValueError("Training dataset is empty.")

    for target in [RISK_TARGET, REVENUE_TARGET, FEASIBILITY_TARGET]:
        if df[target].isna().any():
            raise ValueError(f"Target column has missing values: {target}")


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                "passthrough",
                NUMERIC_FEATURES,
            ),
        ]
    )


def train_risk_model(df: pd.DataFrame) -> tuple[Pipeline, dict, str]:
    X = df[FEATURE_COLUMNS]
    y = df[RISK_TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    model = Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=250,
                    max_depth=18,
                    min_samples_split=8,
                    min_samples_leaf=3,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    report_text = classification_report(y_test, predictions)
    matrix = confusion_matrix(y_test, predictions).tolist()

    metrics = {
        "accuracy": accuracy,
        "confusion_matrix": matrix,
        "target_distribution": y.value_counts().to_dict(),
    }

    return model, metrics, report_text


def train_regression_model(df: pd.DataFrame, target: str) -> tuple[Pipeline, dict]:
    X = df[FEATURE_COLUMNS]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    model = Pipeline(
        steps=[
            ("preprocess", build_preprocessor()),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=250,
                    max_depth=22,
                    min_samples_split=8,
                    min_samples_leaf=3,
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mse = mean_squared_error(y_test, predictions)
    rmse = mse ** 0.5
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    metrics = {
        "target": target,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
    }

    return model, metrics


def save_artifacts(
    risk_model: Pipeline,
    revenue_model: Pipeline,
    feasibility_model: Pipeline,
    metadata: dict,
    report_text: str,
) -> None:
    joblib.dump(risk_model, MODEL_DIR / "risk_classifier.pkl")
    joblib.dump(revenue_model, MODEL_DIR / "revenue_regressor.pkl")
    joblib.dump(feasibility_model, MODEL_DIR / "feasibility_regressor.pkl")

    with open(MODEL_DIR / "model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    with open(REPORT_DIR / "training_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)


def main() -> None:
    ensure_paths()

    df = load_dataset()
    validate_dataset(df)

    # Keep only rows with complete feature values.
    df = df.dropna(subset=FEATURE_COLUMNS + [RISK_TARGET, REVENUE_TARGET, FEASIBILITY_TARGET]).copy()

    print("Training dataset loaded.")
    print(f"Rows: {len(df)}")
    print(f"Features: {len(FEATURE_COLUMNS)}")
    print("\nRisk target distribution:")
    print(df[RISK_TARGET].value_counts().to_string())

    risk_model, risk_metrics, risk_report = train_risk_model(df)
    revenue_model, revenue_metrics = train_regression_model(df, REVENUE_TARGET)
    feasibility_model, feasibility_metrics = train_regression_model(df, FEASIBILITY_TARGET)

    metadata = {
        "trained_at": datetime.utcnow().isoformat() + "Z",
        "dataset_path": str(DATA_PATH),
        "row_count": len(df),
        "feature_count": len(FEATURE_COLUMNS),
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "targets": {
            "risk": RISK_TARGET,
            "revenue": REVENUE_TARGET,
            "feasibility": FEASIBILITY_TARGET,
        },
        "metrics": {
            "risk_classifier": risk_metrics,
            "revenue_regressor": revenue_metrics,
            "feasibility_regressor": feasibility_metrics,
        },
        "important_note": (
            "Models are trained on simulation-based labels generated from real census features "
            "and controlled business assumptions. Predictions should be presented as planning "
            "estimates, not guaranteed real-world financial outcomes."
        ),
    }

    full_report = []
    full_report.append("Zonalyze ML Training Report")
    full_report.append("=" * 32)
    full_report.append(f"Trained at: {metadata['trained_at']}")
    full_report.append(f"Rows used: {len(df)}")
    full_report.append(f"Feature count: {len(FEATURE_COLUMNS)}")
    full_report.append("")
    full_report.append("Risk Classification Metrics")
    full_report.append("-" * 32)
    full_report.append(f"Accuracy: {risk_metrics['accuracy']:.4f}")
    full_report.append("")
    full_report.append(risk_report)
    full_report.append("")
    full_report.append("Revenue Regression Metrics")
    full_report.append("-" * 32)
    full_report.append(f"MAE: {revenue_metrics['mae']:.2f}")
    full_report.append(f"RMSE: {revenue_metrics['rmse']:.2f}")
    full_report.append(f"R2: {revenue_metrics['r2']:.4f}")
    full_report.append("")
    full_report.append("Feasibility Regression Metrics")
    full_report.append("-" * 32)
    full_report.append(f"MAE: {feasibility_metrics['mae']:.2f}")
    full_report.append(f"RMSE: {feasibility_metrics['rmse']:.2f}")
    full_report.append(f"R2: {feasibility_metrics['r2']:.4f}")
    full_report.append("")
    full_report.append("Important note:")
    full_report.append(metadata["important_note"])

    report_text = "\n".join(full_report)

    save_artifacts(
        risk_model=risk_model,
        revenue_model=revenue_model,
        feasibility_model=feasibility_model,
        metadata=metadata,
        report_text=report_text,
    )

    print("\nTraining complete.")
    print("\nRisk classifier:")
    print(f"Accuracy: {risk_metrics['accuracy']:.4f}")
    print("\nRevenue regressor:")
    print(f"MAE: {revenue_metrics['mae']:.2f}")
    print(f"RMSE: {revenue_metrics['rmse']:.2f}")
    print(f"R2: {revenue_metrics['r2']:.4f}")
    print("\nFeasibility regressor:")
    print(f"MAE: {feasibility_metrics['mae']:.2f}")
    print(f"RMSE: {feasibility_metrics['rmse']:.2f}")
    print(f"R2: {feasibility_metrics['r2']:.4f}")

    print("\nCreated model files:")
    print(f"  {MODEL_DIR / 'risk_classifier.pkl'}")
    print(f"  {MODEL_DIR / 'revenue_regressor.pkl'}")
    print(f"  {MODEL_DIR / 'feasibility_regressor.pkl'}")
    print(f"  {MODEL_DIR / 'model_metadata.json'}")
    print(f"  {REPORT_DIR / 'training_report.txt'}")


if __name__ == "__main__":
    main()
