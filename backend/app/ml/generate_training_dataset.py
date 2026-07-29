"""
Zonalyze training dataset generator.

Run from the backend folder:
    python -m app.ml.generate_training_dataset --rows 50000

This generator now delegates all scenario feature/label math to the shared
pipeline in app/ml/feature_pipeline.py, which is the SAME module used at runtime
inference. Municipalities are loaded from the real census "selected features"
file, and business assumptions come from the shared business subcategory catalog,
so training data and live predictions are built from identical logic and inputs.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from app.catalogs.business_subcategories import list_business_subcategory_profiles
from app.ml.feature_pipeline import (
    MODEL_FEATURE_COLUMNS,
    TARGET_COLUMNS,
    BusinessProfile,
    MunicipalitySignals,
    build_scenario_record,
    municipality_signals_from_census_row,
    normalize_business_profile,
)

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"
SELECTED_FEATURES_CSV = DATA_DIR / "processed" / "ontario_csd_selected_features_2021.csv"
DEFAULT_OUTPUT_PATH = GENERATED_DIR / "zonalyze_training_dataset_v2.csv"
RANDOM_SEED = 42

# Radius values a user can realistically request; sampled per training row.
RADIUS_CHOICES = [1, 2, 3, 4, 5, 6, 8, 10, 12]

# Columns written to the training CSV: model features first, then targets.
OUTPUT_COLUMNS = MODEL_FEATURE_COLUMNS + TARGET_COLUMNS


def load_municipality_signals() -> List[MunicipalitySignals]:
    if not SELECTED_FEATURES_CSV.exists():
        raise FileNotFoundError(
            f"Census selected-features file not found: {SELECTED_FEATURES_CSV}. "
            "Copy the census-derived data folder before generating training data."
        )
    df = pd.read_csv(SELECTED_FEATURES_CSV)
    signals: List[MunicipalitySignals] = []
    for _, row in df.iterrows():
        record = row.to_dict()
        if not str(record.get("municipality_name", "")).strip():
            continue
        if float(record.get("population_2021", 0) or 0) <= 0:
            continue
        signals.append(municipality_signals_from_census_row(record))
    if not signals:
        raise RuntimeError("No usable municipality rows found in the census selected-features file.")
    print(f"Loaded {len(signals)} municipality signal rows from {SELECTED_FEATURES_CSV}")
    return signals


def load_business_profiles() -> List[BusinessProfile]:
    profiles = [normalize_business_profile(item) for item in list_business_subcategory_profiles()]
    if not profiles:
        raise RuntimeError("Business subcategory catalog is empty.")
    return profiles


def generate_dataset(rows: int, output_path: Path = DEFAULT_OUTPUT_PATH) -> pd.DataFrame:
    random.seed(RANDOM_SEED)
    rng = np.random.default_rng(RANDOM_SEED)

    municipalities = load_municipality_signals()
    businesses = load_business_profiles()

    generated_rows: List[Dict[str, Any]] = []
    for _ in range(rows):
        muni = random.choice(municipalities)
        biz = random.choice(businesses)
        radius_km = float(random.choice(RADIUS_CHOICES))
        record = build_scenario_record(muni, biz, radius_km, rng=rng)
        generated_rows.append({col: record[col] for col in OUTPUT_COLUMNS})

    df = pd.DataFrame(generated_rows, columns=OUTPUT_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    summary_path = output_path.with_suffix(".summary.json")
    summary = {
        "dataset_version": "v3_unified_pipeline_real_census",
        "row_count": int(len(df)),
        "municipality_count": int(df["municipality_name"].nunique()),
        "business_subcategory_count": int(df["business_subcategory"].nunique()),
        "feature_count": len(MODEL_FEATURE_COLUMNS),
        "source_note": (
            "Municipalities loaded from app/data/processed/ontario_csd_selected_features_2021.csv. "
            "Business assumptions from app.catalogs.business_subcategories. Feature math shared with "
            "runtime inference via app.ml.feature_pipeline.build_scenario_record."
        ),
        "label_note": "Targets remain simulation-generated prototype labels, not observed real-world outcomes.",
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Generated dataset: {output_path}")
    print(json.dumps(summary, indent=2))
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Zonalyze training dataset.")
    parser.add_argument("--rows", type=int, default=50000, help="Number of rows to generate.")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_PATH), help="Output CSV path.")
    args = parser.parse_args()
    generate_dataset(rows=args.rows, output_path=Path(args.output))


if __name__ == "__main__":
    main()
