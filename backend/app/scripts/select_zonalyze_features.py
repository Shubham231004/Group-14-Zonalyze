"""
Zonalyze - Ontario CSD Feature Selection Script

Purpose:
    Takes the processed census model-ready CSV generated from the raw
    Statistics Canada Ontario CSD Census Profile file and creates a smaller,
    cleaner, ML-ready feature dataset for Zonalyze.

Input:
    backend/app/data/processed/ontario_csd_model_ready_2021.csv

Outputs:
    backend/app/data/processed/ontario_csd_selected_features_2021.csv
    backend/app/data/processed/ontario_csd_selected_feature_dictionary_2021.csv

Run from backend/:
    python app/scripts/select_zonalyze_features.py
"""

from pathlib import Path
import pandas as pd


DEFAULT_INPUT = Path("app/data/processed/ontario_csd_model_ready_2021.csv")
DEFAULT_OUTPUT_DIR = Path("app/data/processed")

IDENTITY_COLUMNS = [
    "geo_name_raw",
    "municipality_name",
    "municipality_type",
]

CORE_FEATURE_COLUMNS = [
    "population_2021",
    "population_density_per_km2",
    "population_growth_2016_2021_pct",
    "land_area_km2",
    "population_scale_index_0_100",
    "household_median_total_income_2020",
    "income_index_0_100",
    "children_0_14_pct",
    "youth_15_24_pct",
    "young_adult_20_34_pct",
    "working_age_25_64_pct",
    "seniors_65_plus_pct",
    "median_age",
    "family_with_children_pct",
    "one_person_household_pct",
    "average_household_size",
    "employment_rate_pct",
    "unemployment_rate_pct",
    "participation_rate_pct",
    "immigrant_pct",
    "visible_minority_pct",
    "diversity_index_0_100",
    "renter_pct",
    "renter_average_monthly_shelter_cost",
    "rent_cost_index_0_100",
    "rent_pressure_index_0_100",
    "retail_trade_labour_pct",
    "accommodation_food_labour_pct",
    "other_services_labour_pct",
    "density_index_0_100",
    "market_base_index_0_100",
]

FEATURE_DESCRIPTIONS = {
    "geo_name_raw": "Original geographic name from Statistics Canada.",
    "municipality_name": "Cleaned municipality name used by Zonalyze.",
    "municipality_type": "Municipality type such as city, town, township, or municipality.",
    "population_2021": "Total population in 2021.",
    "population_density_per_km2": "Population density per square kilometre.",
    "population_growth_2016_2021_pct": "Population percentage change from 2016 to 2021.",
    "land_area_km2": "Land area in square kilometres.",
    "population_scale_index_0_100": "Normalized population size index.",
    "household_median_total_income_2020": "Median total household income in 2020.",
    "income_index_0_100": "Normalized income/spending-power index.",
    "children_0_14_pct": "Share of population aged 0 to 14.",
    "youth_15_24_pct": "Share of population aged 15 to 24.",
    "young_adult_20_34_pct": "Share of population aged 20 to 34.",
    "working_age_25_64_pct": "Share of population aged 25 to 64.",
    "seniors_65_plus_pct": "Share of population aged 65 and over.",
    "median_age": "Median age of the population.",
    "family_with_children_pct": "Share of census families with children.",
    "one_person_household_pct": "Share of one-person households.",
    "average_household_size": "Average number of persons per household.",
    "employment_rate_pct": "Employment rate.",
    "unemployment_rate_pct": "Unemployment rate.",
    "participation_rate_pct": "Labour force participation rate.",
    "immigrant_pct": "Share of population that is immigrant.",
    "visible_minority_pct": "Share of population identified as visible minority/racialized population.",
    "diversity_index_0_100": "Derived normalized diversity index.",
    "renter_pct": "Share of households that are renters.",
    "renter_average_monthly_shelter_cost": "Average monthly shelter cost for renter households.",
    "rent_cost_index_0_100": "Normalized renter shelter-cost index.",
    "rent_pressure_index_0_100": "Derived rent and housing pressure index.",
    "retail_trade_labour_pct": "Share of labour force in retail trade.",
    "accommodation_food_labour_pct": "Share of labour force in accommodation and food services.",
    "other_services_labour_pct": "Share of labour force in other services.",
    "density_index_0_100": "Normalized density index.",
    "market_base_index_0_100": "Composite market base index from population, income, density, and demand signals.",
}


def coerce_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def validate_selected_data(df: pd.DataFrame) -> None:
    required = [
        "municipality_name",
        "population_2021",
        "population_density_per_km2",
        "household_median_total_income_2020",
        "market_base_index_0_100",
    ]

    missing_required = [col for col in required if col not in df.columns]
    if missing_required:
        raise ValueError(f"Missing required columns: {missing_required}")

    if df["municipality_name"].duplicated().any():
        duplicates = df.loc[df["municipality_name"].duplicated(), "municipality_name"].head(10).tolist()
        print(f"WARNING: Duplicate municipality names detected. Examples: {duplicates}")

    percentage_columns = [col for col in df.columns if col.endswith("_pct")]
    for col in percentage_columns:
        bad = df[(df[col].notna()) & ((df[col] < 0) | (df[col] > 100))]
        if not bad.empty:
            print(f"WARNING: {col} has {len(bad)} values outside 0-100 range.")

    index_columns = [col for col in df.columns if col.endswith("_0_100")]
    for col in index_columns:
        bad = df[(df[col].notna()) & ((df[col] < 0) | (df[col] > 100))]
        if not bad.empty:
            print(f"WARNING: {col} has {len(bad)} values outside 0-100 range.")

    if (df["population_2021"].fillna(0) <= 0).any():
        print("WARNING: Some municipalities have missing or non-positive population_2021 values.")

    print("\nValidation summary:")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print("\nMissing values by column:")
    missing = df.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if missing.empty:
        print("No missing values found.")
    else:
        print(missing.to_string())


def main() -> None:
    input_path = DEFAULT_INPUT
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Make sure ontario_csd_model_ready_2021.csv exists in app/data/processed/."
        )

    df = pd.read_csv(input_path)

    selected_columns = IDENTITY_COLUMNS + CORE_FEATURE_COLUMNS
    available_columns = [col for col in selected_columns if col in df.columns]
    missing_columns = [col for col in selected_columns if col not in df.columns]

    if missing_columns:
        print("WARNING: The following expected columns were not found and will be skipped:")
        for col in missing_columns:
            print(f"  - {col}")

    selected = df[available_columns].copy()

    numeric_columns = [col for col in selected.columns if col not in IDENTITY_COLUMNS]
    selected = coerce_numeric_columns(selected, numeric_columns)

    selected = selected.dropna(subset=["municipality_name", "population_2021"])
    selected = selected.sort_values("municipality_name").reset_index(drop=True)

    validate_selected_data(selected)

    selected_output = output_dir / "ontario_csd_selected_features_2021.csv"
    dictionary_output = output_dir / "ontario_csd_selected_feature_dictionary_2021.csv"

    selected.to_csv(selected_output, index=False)

    dictionary_rows = []
    for col in selected.columns:
        dictionary_rows.append({
            "column_name": col,
            "description": FEATURE_DESCRIPTIONS.get(col, "Selected Zonalyze feature."),
            "role": "identifier" if col in IDENTITY_COLUMNS else "model_feature",
        })

    pd.DataFrame(dictionary_rows).to_csv(dictionary_output, index=False)

    print("\nCreated:")
    print(f"  {selected_output}")
    print(f"  {dictionary_output}")


if __name__ == "__main__":
    main()
