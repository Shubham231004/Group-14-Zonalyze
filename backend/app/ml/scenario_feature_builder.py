from pathlib import Path
from typing import Any, Dict

import math
import numpy as np
import pandas as pd

from app.catalogs.business_subcategories import list_business_subcategory_profiles
from app.ml.feature_pipeline import (
    TARGET_COLUMNS,
    build_scenario_record,
    municipality_signals_from_census_row,
    normalize_business_profile,
)


APP_DIR = Path(__file__).resolve().parents[1]
CITY_FEATURES_PATH = APP_DIR / "data" / "processed" / "ontario_csd_selected_features_2021.csv"
BUSINESS_TAXONOMY_PATH = APP_DIR / "data" / "synthetic" / "zonalyze_business_taxonomy_seed.csv"

RANDOM_SEED = 42


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_num(row: pd.Series, col: str, default: float = 0.0) -> float:
    val = row.get(col, default)

    if pd.isna(val):
        return default

    return float(val)


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_pct(value: float) -> float:
    return clamp(value / 100.0, 0.0, 1.0)


def load_city_features() -> pd.DataFrame:
    if not CITY_FEATURES_PATH.exists():
        raise FileNotFoundError(f"City feature file not found: {CITY_FEATURES_PATH}")

    return pd.read_csv(CITY_FEATURES_PATH)


def load_business_taxonomy() -> pd.DataFrame:
    """
    Load supported business subcategories from the shared business catalog.

    If the older CSV taxonomy exists, it is merged in for backward
    compatibility. The code-level catalog is the source of the expanded
    subcategory set, while municipalities remain census-data-driven.
    """
    catalog_df = pd.DataFrame(list_business_subcategory_profiles())

    if BUSINESS_TAXONOMY_PATH.exists():
        csv_df = pd.read_csv(BUSINESS_TAXONOMY_PATH)
        combined = pd.concat([csv_df, catalog_df], ignore_index=True, sort=False)
    else:
        combined = catalog_df

    combined["subcategory_key"] = combined["subcategory"].astype(str).str.lower().str.strip()
    combined = combined.drop_duplicates(subset=["subcategory_key"], keep="last")
    return combined.drop(columns=["subcategory_key"])


def get_city_row(municipality_name: str) -> pd.Series:
    df = load_city_features()

    match = df[
        df["municipality_name"].str.lower().str.strip()
        == municipality_name.lower().strip()
    ]

    if match.empty:
        available = df["municipality_name"].dropna().sort_values().head(10).tolist()
        raise ValueError(
            f"Municipality not found: {municipality_name}. "
            f"Example available municipalities: {available}"
        )

    # Ontario has two census subdivisions named "Hamilton": the city (~570k) and a
    # township near Cobourg (~12k). Requests carry only the name, so taking the first
    # row silently answered "Hamilton" with whichever the CSV happened to list first.
    # Pick the largest population — the place a user typing that name means.
    if len(match) > 1 and "population_2021" in match.columns:
        return match.loc[match["population_2021"].idxmax()]

    return match.iloc[0]


def get_business_profile(business_subcategory: str) -> pd.Series:
    df = load_business_taxonomy()

    match = df[
        df["subcategory"].str.lower().str.strip()
        == business_subcategory.lower().strip()
    ]

    if match.empty:
        available = df["subcategory"].dropna().sort_values().head(10).tolist()
        raise ValueError(
            f"Business subcategory not found: {business_subcategory}. "
            f"Example available subcategories: {available}"
        )

    return match.iloc[0]


def radius_population_factor(radius_km: float) -> float:
    factors = {
        1: 0.24,
        3: 0.52,
        5: 0.78,
        10: 1.00,
    }

    return factors.get(int(radius_km), min(1.0, 0.13 * radius_km))


def demographic_fit_score(city: pd.Series, profile: pd.Series) -> float:
    student = normalize_pct(safe_num(city, "youth_15_24_pct", 0))
    young_adult = normalize_pct(safe_num(city, "young_adult_20_34_pct", 0))
    family = normalize_pct(safe_num(city, "family_with_children_pct", 0))
    senior = normalize_pct(safe_num(city, "seniors_65_plus_pct", 0))
    diversity = safe_num(city, "diversity_index_0_100", 0) / 100
    immigrant = normalize_pct(safe_num(city, "immigrant_pct", 0))

    weighted = (
        student * float(profile["student_weight"])
        + young_adult * float(profile["young_adult_weight"])
        + family * float(profile["family_weight"])
        + senior * float(profile["senior_weight"])
        + diversity * float(profile["diversity_weight"])
        + immigrant * float(profile["immigrant_weight"])
    )

    total_weight = (
        float(profile["student_weight"])
        + float(profile["young_adult_weight"])
        + float(profile["family_weight"])
        + float(profile["senior_weight"])
        + float(profile["diversity_weight"])
        + float(profile["immigrant_weight"])
    )

    return round(clamp((weighted / max(total_weight, 0.01)) * 100, 0, 100), 2)


def estimate_competition(city: pd.Series, profile: pd.Series, radius_km: float) -> Dict[str, float]:
    density_idx = safe_num(city, "density_index_0_100", 50) / 100
    market_idx = safe_num(city, "market_base_index_0_100", 50) / 100
    labour_col = str(profile["labour_fit_column"])
    relevant_labour_pct = safe_num(city, labour_col, 5)

    category_factor = relevant_labour_pct / 10.0
    radius_factor = math.sqrt(radius_km)

    expected_competitors = (
        1.5 + 12 * density_idx + 7 * market_idx + 5 * category_factor
    ) * radius_factor

    competitor_count = max(0, int(round(expected_competitors)))

    population = safe_num(city, "population_2021", 10000)
    competitor_density = competitor_count / max(1, population / 10000)

    competition_score = clamp(
        (competitor_density / 10.0) * 100 * float(profile["competition_sensitivity"]),
        0,
        100,
    )

    return {
        "competitor_count_estimate": competitor_count,
        "competitor_density_per_10k": round(competitor_density, 3),
        "competition_score_0_100": round(competition_score, 2),
    }


def estimate_lease_cost(city: pd.Series, profile: pd.Series, radius_km: float) -> float:
    rent_index = safe_num(city, "rent_cost_index_0_100", 50) / 100
    density_index = safe_num(city, "density_index_0_100", 50) / 100

    base_price_per_sqft_year = 14 + (rent_index * 22) + (density_index * 7)
    radius_discount = {
        1: 1.04,
        3: 1.01,
        5: 0.98,
        10: 0.92,
    }.get(int(radius_km), 1.0)

    sqft = float(profile["space_sqft"])
    annual_lease = base_price_per_sqft_year * sqft * radius_discount
    monthly_lease = annual_lease / 12

    return round(max(750, monthly_lease), 2)


def demand_score(city: pd.Series, profile: pd.Series, competition_score: float) -> float:
    demo_fit = demographic_fit_score(city, profile)
    income_idx = safe_num(city, "income_index_0_100", 50)
    density_idx = safe_num(city, "density_index_0_100", 50)
    market_idx = safe_num(city, "market_base_index_0_100", 50)
    employment = safe_num(city, "employment_rate_pct", 55)

    income_component = income_idx * float(profile["income_sensitivity"])
    density_component = density_idx * float(profile["density_sensitivity"])

    raw = (
        12
        + demo_fit * 0.32
        + market_idx * 0.23
        + income_component * 0.14
        + density_component * 0.13
        + employment * 0.12
        - competition_score * 0.10
    )

    return round(clamp(raw, 0, 100), 2)


def add_model_schema_aliases(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Align runtime feature names with the Step 18 trained model schema.

    Runtime services use source-oriented names from census/evidence files, while
    the retrained models expect normalized names generated by
    generate_training_dataset.py. This function maps equivalent fields so the
    predictor does not fill important model inputs with zero defaults.
    """

    monthly_lease = safe_float(features.get("monthly_lease_cost_estimate"), 0.0)
    gross_revenue = safe_float(features.get("gross_revenue_monthly"), 0.0)
    operating_cost = safe_float(features.get("monthly_operating_cost_estimate"), 0.0)
    target_customer_pool = safe_float(features.get("target_customer_pool_estimate"), 0.0)
    avg_ticket = safe_float(features.get("average_ticket_size"), 0.0)

    # Categorical model fields
    features["business_group"] = (
        features.get("business_group")
        or features.get("business_category")
        or "General Local Business"
    )

    # Census/demographic aliases expected by the Step 18 model
    features["population_density"] = safe_float(
        features.get("population_density")
        or features.get("population_density_per_km2")
        or features.get("density_index_0_100"),
        0.0,
    )
    features["median_income"] = safe_float(
        features.get("median_income")
        or features.get("household_median_total_income_2020")
        or features.get("household_median_after_tax_income_2020"),
        0.0,
    )
    features["median_age"] = safe_float(
        features.get("median_age")
        or features.get("average_age"),
        0.0,
    )
    features["household_count"] = safe_float(
        features.get("household_count")
        or features.get("private_households_total")
        or features.get("private_dwellings_occupied"),
        0.0,
    )
    features["employment_rate"] = safe_float(
        features.get("employment_rate")
        or features.get("employment_rate_pct"),
        0.0,
    )
    features["diversity_index"] = safe_float(
        features.get("diversity_index")
        or features.get("diversity_index_0_100"),
        0.0,
    )
    features["students_pct"] = safe_float(
        features.get("students_pct")
        or features.get("youth_15_24_pct"),
        0.0,
    )
    features["families_pct"] = safe_float(
        features.get("families_pct")
        or features.get("family_with_children_pct"),
        0.0,
    )
    features["retirees_pct"] = safe_float(
        features.get("retirees_pct")
        or features.get("seniors_65_plus_pct"),
        0.0,
    )

    # Business-catalog aliases expected by the Step 18 model
    features["target_customer_rate"] = safe_float(
        features.get("target_customer_rate")
        or features.get("base_capture_rate"),
        0.0,
    )
    features["lease_sensitivity"] = safe_float(features.get("lease_sensitivity"), 1.0)
    features["competition_sensitivity"] = safe_float(features.get("competition_sensitivity"), 1.0)
    features["demand_sensitivity"] = safe_float(features.get("demand_sensitivity"), 1.0)

    # Evidence/analysis aliases expected by the Step 18 model
    features["demographic_fit_score"] = safe_float(
        features.get("demographic_fit_score")
        or features.get("demographic_fit_score_0_100"),
        0.0,
    )
    features["competitor_count_same_type"] = safe_float(
        features.get("competitor_count_same_type")
        or features.get("competitor_count_estimate"),
        0.0,
    )
    features["competition_pressure_index"] = safe_float(
        features.get("competition_pressure_index")
        or features.get("competition_score_0_100"),
        0.0,
    )
    features["low_monthly_lease_cost"] = safe_float(
        features.get("low_monthly_lease_cost")
        or features.get("lease_cost_low_estimate"),
        monthly_lease * 0.75 if monthly_lease else 0.0,
    )
    features["median_monthly_lease_cost"] = safe_float(
        features.get("median_monthly_lease_cost")
        or features.get("monthly_lease_cost_estimate"),
        0.0,
    )
    features["high_monthly_lease_cost"] = safe_float(
        features.get("high_monthly_lease_cost")
        or features.get("lease_cost_high_estimate"),
        monthly_lease * 1.25 if monthly_lease else 0.0,
    )
    features["rent_pressure_index"] = safe_float(
        features.get("rent_pressure_index")
        or features.get("rent_pressure_index_0_100"),
        0.0,
    )
    features["demand_pressure_index"] = safe_float(
        features.get("demand_pressure_index")
        or features.get("demand_score_0_100"),
        0.0,
    )

    expected_customers = safe_float(features.get("expected_customers_per_day"), 0.0)
    if expected_customers <= 0:
        expected_customers = max(1.0, target_customer_pool / 30.0)
    features["expected_customers_per_day"] = expected_customers

    if gross_revenue <= 0:
        gross_revenue = expected_customers * avg_ticket * 30.0
    features["gross_revenue_monthly"] = round(gross_revenue, 2)

    features["lease_burden_ratio"] = safe_float(
        features.get("lease_burden_ratio"),
        monthly_lease / max(1.0, gross_revenue),
    )
    features["profit_margin_pct"] = safe_float(
        features.get("profit_margin_pct"),
        ((gross_revenue - operating_cost) / max(1.0, gross_revenue)) * 100.0,
    )

    return features


def build_prediction_features(
    municipality_name: str,
    business_subcategory: str,
    radius_km: float,
) -> Dict[str, Any]:
    """Build the deterministic feature row for a single scenario.

    This delegates all model-feature math to the shared pipeline
    (app.ml.feature_pipeline.build_scenario_record) so runtime inputs match the
    training data exactly. On top of the model feature columns it adds census
    passthrough fields and legacy aliases that the evidence/analysis services
    still read, so nothing downstream breaks.
    """
    city = get_city_row(municipality_name)
    profile = get_business_profile(business_subcategory)

    muni = municipality_signals_from_census_row(city)
    biz = normalize_business_profile(profile.to_dict())

    record = build_scenario_record(muni, biz, radius_km, rng=None)

    # Model features + display cost components; drop simulation target labels.
    features: Dict[str, Any] = {
        key: value for key, value in record.items() if key not in set(TARGET_COLUMNS)
    }

    # Census passthroughs (real values) and legacy aliases consumed by the
    # competition / demand / lease / credibility / explanation services.
    features.update(
        {
            "municipality_type": city.get("municipality_type"),
            "business_category": profile["category"],
            "municipality": muni.municipality_name,
            # census passthroughs
            "population_density_per_km2": muni.population_density,
            "household_median_total_income_2020": muni.median_income,
            "average_age": muni.median_age,
            "employment_rate_pct": muni.employment_rate,
            "diversity_index_0_100": muni.diversity_index,
            "youth_15_24_pct": muni.students_pct,
            "family_with_children_pct": muni.families_pct,
            "seniors_65_plus_pct": muni.retirees_pct,
            "income_index_0_100": muni.income_index,
            "density_index_0_100": muni.density_index,
            "market_base_index_0_100": muni.market_base_index,
            "rent_pressure_index_0_100": safe_num(city, "rent_pressure_index_0_100", 50.0),
            "renter_average_monthly_shelter_cost": safe_num(city, "renter_average_monthly_shelter_cost", 0.0),
            "base_capture_rate": biz.base_capture_rate,
            "gross_margin_pct": float(profile.get("gross_margin_pct", 0.4)) * 100,
            # aliases for legacy field names
            "demographic_fit_score_0_100": record["demographic_fit_score"],
            "business_type_demographic_fit": record["demographic_fit_score"],
            "competitor_count_estimate": record["competitor_count_same_type"],
            "foot_traffic_proxy": record["foot_traffic_proxy_index"],
            "transit_access_score": record["transit_access_proxy_index"],
            "monthly_lease_cost_estimate": record["median_monthly_lease_cost"],
            "estimated_monthly_lease_cost": record["median_monthly_lease_cost"],
            "lease_cost_low_estimate": record["low_monthly_lease_cost"],
            "lease_cost_high_estimate": record["high_monthly_lease_cost"],
            "monthly_utilities_marketing_cost_estimate": round(
                record["monthly_utilities_cost_estimate"] + record["monthly_marketing_cost_estimate"], 2
            ),
        }
    )

    return features
