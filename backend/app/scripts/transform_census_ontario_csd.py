"""
transform_census_ontario_csd.py

Transforms Statistics Canada 2021 Census Profile data for Ontario Census Subdivisions (CSDs)
from long format into a clean, city-level feature table for Zonalyze.

Expected raw file:
    backend/app/data/raw/98-401-X2021021_English_CSV_data.csv

Outputs:
    backend/app/data/processed/ontario_csd_features_2021.csv
    backend/app/data/processed/ontario_csd_model_ready_2021.csv
    backend/app/data/processed/ontario_csd_feature_dictionary_2021.csv

Run from backend folder:
    python -m app.scripts.transform_census_ontario_csd

Or run directly:
    python backend/app/scripts/transform_census_ontario_csd.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

ValueSource = Literal["count", "rate"]

# Characteristic IDs are more reliable than matching long text labels.
# These IDs come from the StatCan Census Profile metadata for this exact CSD Ontario file.
FEATURE_SPECS: dict[int, tuple[str, ValueSource]] = {
    # Core geography / population
    1: ("population_2021", "count"),
    2: ("population_2016", "count"),
    3: ("population_growth_2016_2021_pct", "rate"),
    4: ("private_dwellings_total", "count"),
    5: ("private_dwellings_occupied", "count"),
    6: ("population_density_per_km2", "count"),
    7: ("land_area_km2", "count"),

    # Age groups. We use counts and calculate percentages ourselves.
    9: ("age_0_14_count", "count"),
    14: ("age_15_19_count", "count"),
    15: ("age_20_24_count", "count"),
    16: ("age_25_29_count", "count"),
    17: ("age_30_34_count", "count"),
    18: ("age_35_39_count", "count"),
    19: ("age_40_44_count", "count"),
    20: ("age_45_49_count", "count"),
    21: ("age_50_54_count", "count"),
    22: ("age_55_59_count", "count"),
    23: ("age_60_64_count", "count"),
    24: ("age_65_plus_count", "count"),
    39: ("average_age", "count"),
    40: ("median_age", "count"),

    # Households and family structure
    50: ("private_households_total", "count"),
    55: ("large_households_5_plus_count", "count"),
    57: ("average_household_size", "count"),
    78: ("census_families_total", "count"),
    81: ("married_couples_with_children_count", "count"),
    84: ("common_law_couples_with_children_count", "count"),
    86: ("one_parent_families_count", "count"),
    110: ("one_person_households_count", "count"),

    # Income and affordability
    243: ("household_median_total_income_2020", "count"),
    244: ("household_median_after_tax_income_2020", "count"),
    252: ("household_average_total_income_2020", "count"),
    253: ("household_average_after_tax_income_2020", "count"),
    345: ("low_income_prevalence_pct", "rate"),
    379: ("gini_household_total_income", "count"),

    # Housing cost proxies. These are residential, not commercial lease values.
    1415: ("owner_households_count", "count"),
    1416: ("renter_households_count", "count"),
    1494: ("renter_median_monthly_shelter_cost", "count"),
    1495: ("renter_average_monthly_shelter_cost", "count"),

    # Immigration and diversity proxies
    1529: ("immigrants_count", "count"),
    1537: ("non_permanent_residents_count", "count"),
    1684: ("visible_minority_count", "count"),

    # Labour force
    2228: ("participation_rate_pct", "rate"),
    2229: ("employment_rate_pct", "rate"),
    2230: ("unemployment_rate_pct", "rate"),

    # Local labour/business environment proxies
    2261: ("all_industries_labour_count", "count"),
    2268: ("retail_trade_labour_count", "count"),
    2279: ("accommodation_food_labour_count", "count"),
    2280: ("other_services_labour_count", "count"),

    # Commuting / accessibility proxy
    2603: ("commuting_mode_total_count", "count"),
    2607: ("public_transit_commuters_count", "count"),
    2608: ("walked_commuters_count", "count"),
    2609: ("bicycle_commuters_count", "count"),
}

ESSENTIAL_COLUMNS = [
    "alt_geo_code",
    "dguid",
    "geo_name_raw",
    "municipality_name",
    "municipality_type",
    "population_2021",
    "population_density_per_km2",
    "household_median_total_income_2020",
    "youth_15_24_pct",
    "young_adult_20_34_pct",
    "working_age_25_64_pct",
    "seniors_65_plus_pct",
    "family_with_children_pct",
    "employment_rate_pct",
    "renter_average_monthly_shelter_cost",
    "renter_pct",
    "immigrant_pct",
    "visible_minority_pct",
    "diversity_index_0_100",
    "rent_pressure_index_0_100",
    "data_quality_flag",
    "tnr_sf",
    "tnr_lf",
]


def clean_municipality_name(raw_name: str) -> str:
    """Convert 'Kitchener, City (CY)' into 'Kitchener'."""
    if not isinstance(raw_name, str):
        return ""
    return re.sub(r",\s*[^,]+\s*\([A-Z]+\)$", "", raw_name).strip()


def extract_municipality_type(raw_name: str) -> str:
    """Extract type from 'Kitchener, City (CY)' as 'CY'."""
    if not isinstance(raw_name, str):
        return ""
    match = re.search(r"\(([A-Z]+)\)\s*$", raw_name)
    return match.group(1) if match else ""


def safe_pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace({0: np.nan})
    return (numerator / denominator * 100).replace([np.inf, -np.inf], np.nan)


def minmax_0_100(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().sum() == 0:
        return pd.Series(np.nan, index=s.index)
    min_value = s.min()
    max_value = s.max()
    if pd.isna(min_value) or pd.isna(max_value) or max_value == min_value:
        return pd.Series(50.0, index=s.index)
    return ((s - min_value) / (max_value - min_value) * 100).clip(0, 100)


def read_filtered_census(raw_path: Path, chunksize: int = 250_000) -> pd.DataFrame:
    usecols = [
        "CENSUS_YEAR",
        "DGUID",
        "ALT_GEO_CODE",
        "GEO_LEVEL",
        "GEO_NAME",
        "TNR_SF",
        "TNR_LF",
        "DATA_QUALITY_FLAG",
        "CHARACTERISTIC_ID",
        "CHARACTERISTIC_NAME",
        "C1_COUNT_TOTAL",
        "C10_RATE_TOTAL",
    ]

    keep_ids = set(FEATURE_SPECS.keys())
    frames: list[pd.DataFrame] = []

    for chunk in pd.read_csv(
        raw_path,
        usecols=usecols,
        encoding="latin1",
        chunksize=chunksize,
        low_memory=False,
    ):
        chunk = chunk[chunk["CHARACTERISTIC_ID"].isin(keep_ids)].copy()
        if not chunk.empty:
            frames.append(chunk)

    if not frames:
        raise ValueError("No matching characteristic IDs were found in the raw census file.")

    return pd.concat(frames, ignore_index=True)


def transform(raw_path: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    filtered = read_filtered_census(raw_path)

    filtered["feature_name"] = filtered["CHARACTERISTIC_ID"].map(
        lambda cid: FEATURE_SPECS[int(cid)][0]
    )
    filtered["value_source"] = filtered["CHARACTERISTIC_ID"].map(
        lambda cid: FEATURE_SPECS[int(cid)][1]
    )

    filtered["C1_COUNT_TOTAL"] = pd.to_numeric(filtered["C1_COUNT_TOTAL"], errors="coerce")
    filtered["C10_RATE_TOTAL"] = pd.to_numeric(filtered["C10_RATE_TOTAL"], errors="coerce")

    filtered["feature_value"] = np.where(
        filtered["value_source"].eq("rate"),
        filtered["C10_RATE_TOTAL"],
        filtered["C1_COUNT_TOTAL"],
    )

    geo_cols = [
        "CENSUS_YEAR",
        "DGUID",
        "ALT_GEO_CODE",
        "GEO_LEVEL",
        "GEO_NAME",
        "TNR_SF",
        "TNR_LF",
        "DATA_QUALITY_FLAG",
    ]

    wide = (
        filtered.pivot_table(
            index=geo_cols,
            columns="feature_name",
            values="feature_value",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    wide = wide.rename(
        columns={
            "CENSUS_YEAR": "census_year",
            "DGUID": "dguid",
            "ALT_GEO_CODE": "alt_geo_code",
            "GEO_LEVEL": "geo_level",
            "GEO_NAME": "geo_name_raw",
            "TNR_SF": "tnr_sf",
            "TNR_LF": "tnr_lf",
            "DATA_QUALITY_FLAG": "data_quality_flag",
        }
    )

    wide["municipality_name"] = wide["geo_name_raw"].map(clean_municipality_name)
    wide["municipality_type"] = wide["geo_name_raw"].map(extract_municipality_type)

    # Derived demographic features.
    pop = wide["population_2021"]

    wide["children_0_14_pct"] = safe_pct(wide["age_0_14_count"], pop)
    wide["youth_15_24_count"] = wide["age_15_19_count"] + wide["age_20_24_count"]
    wide["youth_15_24_pct"] = safe_pct(wide["youth_15_24_count"], pop)

    wide["young_adult_20_34_count"] = (
        wide["age_20_24_count"] + wide["age_25_29_count"] + wide["age_30_34_count"]
    )
    wide["young_adult_20_34_pct"] = safe_pct(wide["young_adult_20_34_count"], pop)

    working_age_cols = [
        "age_25_29_count",
        "age_30_34_count",
        "age_35_39_count",
        "age_40_44_count",
        "age_45_49_count",
        "age_50_54_count",
        "age_55_59_count",
        "age_60_64_count",
    ]
    wide["working_age_25_64_count"] = wide[working_age_cols].sum(axis=1, min_count=1)
    wide["working_age_25_64_pct"] = safe_pct(wide["working_age_25_64_count"], pop)
    wide["seniors_65_plus_pct"] = safe_pct(wide["age_65_plus_count"], pop)

    # Household and family features.
    wide["family_with_children_count"] = (
        wide["married_couples_with_children_count"].fillna(0)
        + wide["common_law_couples_with_children_count"].fillna(0)
        + wide["one_parent_families_count"].fillna(0)
    )
    wide["family_with_children_pct"] = safe_pct(
        wide["family_with_children_count"], wide["census_families_total"]
    )
    wide["large_household_pct"] = safe_pct(
        wide["large_households_5_plus_count"], wide["private_households_total"]
    )
    wide["one_person_household_pct"] = safe_pct(
        wide["one_person_households_count"], wide["private_households_total"]
    )

    # Housing / rent pressure features.
    wide["renter_pct"] = safe_pct(
        wide["renter_households_count"],
        wide["owner_households_count"].fillna(0) + wide["renter_households_count"].fillna(0),
    )

    # Diversity features. These are proxies, not direct demand labels.
    wide["immigrant_pct"] = safe_pct(wide["immigrants_count"], pop)
    wide["non_permanent_residents_pct"] = safe_pct(wide["non_permanent_residents_count"], pop)
    wide["visible_minority_pct"] = safe_pct(wide["visible_minority_count"], pop)
    wide["diversity_index_0_100"] = (
        0.50 * wide["visible_minority_pct"].fillna(0)
        + 0.35 * wide["immigrant_pct"].fillna(0)
        + 0.15 * wide["non_permanent_residents_pct"].fillna(0)
    ).clip(0, 100)

    # Local employment / business environment proxies.
    wide["retail_trade_labour_pct"] = safe_pct(
        wide["retail_trade_labour_count"], wide["all_industries_labour_count"]
    )
    wide["accommodation_food_labour_pct"] = safe_pct(
        wide["accommodation_food_labour_count"], wide["all_industries_labour_count"]
    )
    wide["other_services_labour_pct"] = safe_pct(
        wide["other_services_labour_count"], wide["all_industries_labour_count"]
    )

    # Accessibility proxy.
    wide["transit_walk_bike_commuters_count"] = (
        wide["public_transit_commuters_count"].fillna(0)
        + wide["walked_commuters_count"].fillna(0)
        + wide["bicycle_commuters_count"].fillna(0)
    )
    wide["transit_walk_bike_pct"] = safe_pct(
        wide["transit_walk_bike_commuters_count"], wide["commuting_mode_total_count"]
    )

    # Normalized indices that are useful for rules and model features.
    wide["population_scale_index_0_100"] = minmax_0_100(np.log1p(wide["population_2021"]))
    wide["income_index_0_100"] = minmax_0_100(wide["household_median_total_income_2020"])
    wide["density_index_0_100"] = minmax_0_100(np.log1p(wide["population_density_per_km2"]))
    wide["rent_cost_index_0_100"] = minmax_0_100(wide["renter_average_monthly_shelter_cost"])
    wide["rent_pressure_index_0_100"] = (
        0.70 * wide["rent_cost_index_0_100"].fillna(0)
        + 0.30 * wide["renter_pct"].fillna(0)
    ).clip(0, 100)

    # Broad market opportunity index. This is NOT a prediction target.
    # It is an engineered input feature for downstream rule-based or ML modules.
    wide["market_base_index_0_100"] = (
        0.30 * wide["population_scale_index_0_100"].fillna(0)
        + 0.20 * wide["density_index_0_100"].fillna(0)
        + 0.20 * wide["income_index_0_100"].fillna(0)
        + 0.15 * wide["employment_rate_pct"].fillna(0)
        + 0.15 * wide["transit_walk_bike_pct"].fillna(0)
    ).clip(0, 100)

    # Keep readable ordering: identifiers, essential engineered columns, then all raw extracted columns.
    identifier_cols = [
        "census_year",
        "dguid",
        "alt_geo_code",
        "geo_level",
        "geo_name_raw",
        "municipality_name",
        "municipality_type",
        "data_quality_flag",
        "tnr_sf",
        "tnr_lf",
    ]
    engineered_cols = [
        "children_0_14_pct",
        "youth_15_24_count",
        "youth_15_24_pct",
        "young_adult_20_34_count",
        "young_adult_20_34_pct",
        "working_age_25_64_count",
        "working_age_25_64_pct",
        "seniors_65_plus_pct",
        "family_with_children_count",
        "family_with_children_pct",
        "large_household_pct",
        "one_person_household_pct",
        "renter_pct",
        "immigrant_pct",
        "non_permanent_residents_pct",
        "visible_minority_pct",
        "diversity_index_0_100",
        "retail_trade_labour_pct",
        "accommodation_food_labour_pct",
        "other_services_labour_pct",
        "transit_walk_bike_commuters_count",
        "transit_walk_bike_pct",
        "population_scale_index_0_100",
        "income_index_0_100",
        "density_index_0_100",
        "rent_cost_index_0_100",
        "rent_pressure_index_0_100",
        "market_base_index_0_100",
    ]
    remaining_cols = [
        c
        for c in wide.columns
        if c not in identifier_cols and c not in engineered_cols
    ]
    wide = wide[identifier_cols + engineered_cols + remaining_cols]

    # Round for storage/readability.
    numeric_cols = wide.select_dtypes(include=["number"]).columns
    wide[numeric_cols] = wide[numeric_cols].round(4)

    full_output = output_dir / "ontario_csd_features_2021.csv"
    wide.to_csv(full_output, index=False)

    # Model-ready means we keep only rows with enough base data to safely calculate scenario features.
    required_for_model = [
        "population_2021",
        "population_density_per_km2",
        "household_median_total_income_2020",
        "youth_15_24_pct",
        "young_adult_20_34_pct",
        "working_age_25_64_pct",
        "seniors_65_plus_pct",
        "employment_rate_pct",
        "rent_pressure_index_0_100",
        "market_base_index_0_100",
    ]
    model_ready = wide.copy()
    model_ready = model_ready[model_ready["population_2021"].fillna(0) >= 1000]
    model_ready = model_ready.dropna(subset=required_for_model)

    model_ready_output = output_dir / "ontario_csd_model_ready_2021.csv"
    model_ready.to_csv(model_ready_output, index=False)

    feature_dictionary_rows = []
    for cid, (feature_name, value_source) in FEATURE_SPECS.items():
        feature_dictionary_rows.append(
            {
                "characteristic_id": cid,
                "feature_name": feature_name,
                "value_source": value_source,
            }
        )
    feature_dictionary = pd.DataFrame(feature_dictionary_rows).sort_values("characteristic_id")
    feature_dictionary_output = output_dir / "ontario_csd_feature_dictionary_2021.csv"
    feature_dictionary.to_csv(feature_dictionary_output, index=False)

    print("Transformation completed.")
    print(f"Full feature file: {full_output}")
    print(f"Model-ready file: {model_ready_output}")
    print(f"Feature dictionary: {feature_dictionary_output}")
    print(f"Full rows: {len(wide):,}")
    print(f"Model-ready rows: {len(model_ready):,}")

    return full_output, model_ready_output, feature_dictionary_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform Ontario CSD Census Profile data for Zonalyze.")
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("app/data/raw/98-401-X2021021_English_CSV_data.csv"),
        help="Path to the raw Statistics Canada CSV data file.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("app/data/processed"),
        help="Output directory for processed files.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.raw.exists():
        raise FileNotFoundError(
            f"Raw file not found: {args.raw}\n"
            "Place the StatCan CSV in backend/app/data/raw/ or pass --raw PATH."
        )
    transform(args.raw, args.out)
