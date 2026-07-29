"""
Zonalyze - Synthetic Scenario Dataset Generator V2

Purpose:
    Expands the cleaned Ontario CSD census feature dataset into a balanced,
    explainable synthetic business-scenario dataset.

Input:
    app/data/processed/ontario_csd_selected_features_2021.csv

Outputs:
    app/data/synthetic/zonalyze_synthetic_scenarios_2021.csv
    app/data/synthetic/zonalyze_business_taxonomy_seed.csv
    app/data/synthetic/zonalyze_synthetic_dataset_dictionary.csv

Run from backend/:
    python app/scripts/generate_synthetic_scenarios.py

Notes:
    Census-based city features are real.
    Business variables and output labels are generated through controlled
    assumptions and formulas.
    V2 calibration reduces excessive high-risk / not-recommended bias.
"""

from __future__ import annotations

from pathlib import Path
import math
import random
from typing import Dict, List

import numpy as np
import pandas as pd


RANDOM_SEED = 42
DEFAULT_INPUT = Path("app/data/processed/ontario_csd_selected_features_2021.csv")
DEFAULT_OUTPUT_DIR = Path("app/data/synthetic")
OUTPUT_SCENARIOS = "zonalyze_synthetic_scenarios_2021.csv"
OUTPUT_TAXONOMY = "zonalyze_business_taxonomy_seed.csv"
OUTPUT_DICTIONARY = "zonalyze_synthetic_dataset_dictionary.csv"

RADII_KM = [1, 3, 5, 10]
MAX_ROWS = 50000


BUSINESS_TAXONOMY: List[Dict[str, object]] = [
    {
        "category": "Grocery and Food Retail",
        "subcategory": "General Grocery Store",
        "avg_ticket": 42,
        "base_capture_rate": 0.014,
        "gross_margin_pct": 0.32,
        "space_sqft": 4500,
        "monthly_staff_cost": 23000,
        "monthly_utilities": 3900,
        "competition_sensitivity": 0.62,
        "income_sensitivity": 0.35,
        "density_sensitivity": 0.55,
        "student_weight": 0.15,
        "young_adult_weight": 0.20,
        "family_weight": 0.45,
        "senior_weight": 0.20,
        "diversity_weight": 0.20,
        "immigrant_weight": 0.20,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Grocery and Food Retail",
        "subcategory": "Indian Grocery Store",
        "avg_ticket": 38,
        "base_capture_rate": 0.009,
        "gross_margin_pct": 0.35,
        "space_sqft": 2800,
        "monthly_staff_cost": 14000,
        "monthly_utilities": 2600,
        "competition_sensitivity": 0.52,
        "income_sensitivity": 0.30,
        "density_sensitivity": 0.60,
        "student_weight": 0.12,
        "young_adult_weight": 0.22,
        "family_weight": 0.38,
        "senior_weight": 0.12,
        "diversity_weight": 0.75,
        "immigrant_weight": 0.85,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Grocery and Food Retail",
        "subcategory": "Chinese Grocery Store",
        "avg_ticket": 40,
        "base_capture_rate": 0.0085,
        "gross_margin_pct": 0.34,
        "space_sqft": 3000,
        "monthly_staff_cost": 15000,
        "monthly_utilities": 2700,
        "competition_sensitivity": 0.52,
        "income_sensitivity": 0.32,
        "density_sensitivity": 0.62,
        "student_weight": 0.12,
        "young_adult_weight": 0.22,
        "family_weight": 0.38,
        "senior_weight": 0.12,
        "diversity_weight": 0.78,
        "immigrant_weight": 0.82,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Grocery and Food Retail",
        "subcategory": "Jamaican Grocery Store",
        "avg_ticket": 35,
        "base_capture_rate": 0.0078,
        "gross_margin_pct": 0.36,
        "space_sqft": 2200,
        "monthly_staff_cost": 12000,
        "monthly_utilities": 2300,
        "competition_sensitivity": 0.48,
        "income_sensitivity": 0.25,
        "density_sensitivity": 0.58,
        "student_weight": 0.12,
        "young_adult_weight": 0.22,
        "family_weight": 0.35,
        "senior_weight": 0.12,
        "diversity_weight": 0.80,
        "immigrant_weight": 0.75,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Grocery and Food Retail",
        "subcategory": "Halal Grocery Store",
        "avg_ticket": 37,
        "base_capture_rate": 0.0085,
        "gross_margin_pct": 0.36,
        "space_sqft": 2400,
        "monthly_staff_cost": 12500,
        "monthly_utilities": 2450,
        "competition_sensitivity": 0.48,
        "income_sensitivity": 0.25,
        "density_sensitivity": 0.60,
        "student_weight": 0.10,
        "young_adult_weight": 0.22,
        "family_weight": 0.42,
        "senior_weight": 0.10,
        "diversity_weight": 0.84,
        "immigrant_weight": 0.82,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Grocery and Food Retail",
        "subcategory": "Organic Grocery Store",
        "avg_ticket": 52,
        "base_capture_rate": 0.0065,
        "gross_margin_pct": 0.39,
        "space_sqft": 2600,
        "monthly_staff_cost": 13000,
        "monthly_utilities": 2450,
        "competition_sensitivity": 0.50,
        "income_sensitivity": 0.75,
        "density_sensitivity": 0.65,
        "student_weight": 0.14,
        "young_adult_weight": 0.34,
        "family_weight": 0.34,
        "senior_weight": 0.14,
        "diversity_weight": 0.25,
        "immigrant_weight": 0.20,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Restaurants and Food Services",
        "subcategory": "Casual Restaurant",
        "avg_ticket": 28,
        "base_capture_rate": 0.010,
        "gross_margin_pct": 0.62,
        "space_sqft": 2800,
        "monthly_staff_cost": 26000,
        "monthly_utilities": 4600,
        "competition_sensitivity": 0.66,
        "income_sensitivity": 0.45,
        "density_sensitivity": 0.65,
        "student_weight": 0.20,
        "young_adult_weight": 0.32,
        "family_weight": 0.32,
        "senior_weight": 0.10,
        "diversity_weight": 0.25,
        "immigrant_weight": 0.20,
        "labour_fit_column": "accommodation_food_labour_pct",
    },
    {
        "category": "Restaurants and Food Services",
        "subcategory": "Indian Restaurant",
        "avg_ticket": 27,
        "base_capture_rate": 0.0082,
        "gross_margin_pct": 0.64,
        "space_sqft": 2400,
        "monthly_staff_cost": 22000,
        "monthly_utilities": 4200,
        "competition_sensitivity": 0.58,
        "income_sensitivity": 0.42,
        "density_sensitivity": 0.68,
        "student_weight": 0.18,
        "young_adult_weight": 0.32,
        "family_weight": 0.30,
        "senior_weight": 0.08,
        "diversity_weight": 0.76,
        "immigrant_weight": 0.82,
        "labour_fit_column": "accommodation_food_labour_pct",
    },
    {
        "category": "Restaurants and Food Services",
        "subcategory": "Chinese Restaurant",
        "avg_ticket": 25,
        "base_capture_rate": 0.0085,
        "gross_margin_pct": 0.64,
        "space_sqft": 2400,
        "monthly_staff_cost": 21500,
        "monthly_utilities": 4200,
        "competition_sensitivity": 0.60,
        "income_sensitivity": 0.40,
        "density_sensitivity": 0.68,
        "student_weight": 0.18,
        "young_adult_weight": 0.30,
        "family_weight": 0.32,
        "senior_weight": 0.10,
        "diversity_weight": 0.78,
        "immigrant_weight": 0.80,
        "labour_fit_column": "accommodation_food_labour_pct",
    },
    {
        "category": "Restaurants and Food Services",
        "subcategory": "Jamaican Restaurant",
        "avg_ticket": 24,
        "base_capture_rate": 0.0072,
        "gross_margin_pct": 0.65,
        "space_sqft": 1800,
        "monthly_staff_cost": 18000,
        "monthly_utilities": 3500,
        "competition_sensitivity": 0.52,
        "income_sensitivity": 0.35,
        "density_sensitivity": 0.62,
        "student_weight": 0.20,
        "young_adult_weight": 0.32,
        "family_weight": 0.26,
        "senior_weight": 0.08,
        "diversity_weight": 0.80,
        "immigrant_weight": 0.75,
        "labour_fit_column": "accommodation_food_labour_pct",
    },
    {
        "category": "Restaurants and Food Services",
        "subcategory": "Vegan Restaurant",
        "avg_ticket": 29,
        "base_capture_rate": 0.0068,
        "gross_margin_pct": 0.66,
        "space_sqft": 1700,
        "monthly_staff_cost": 17000,
        "monthly_utilities": 3300,
        "competition_sensitivity": 0.43,
        "income_sensitivity": 0.70,
        "density_sensitivity": 0.70,
        "student_weight": 0.20,
        "young_adult_weight": 0.42,
        "family_weight": 0.20,
        "senior_weight": 0.10,
        "diversity_weight": 0.35,
        "immigrant_weight": 0.20,
        "labour_fit_column": "accommodation_food_labour_pct",
    },
    {
        "category": "Restaurants and Food Services",
        "subcategory": "Coffee Shop / Cafe",
        "avg_ticket": 10,
        "base_capture_rate": 0.017,
        "gross_margin_pct": 0.70,
        "space_sqft": 1400,
        "monthly_staff_cost": 13500,
        "monthly_utilities": 2100,
        "competition_sensitivity": 0.70,
        "income_sensitivity": 0.45,
        "density_sensitivity": 0.80,
        "student_weight": 0.45,
        "young_adult_weight": 0.35,
        "family_weight": 0.12,
        "senior_weight": 0.08,
        "diversity_weight": 0.20,
        "immigrant_weight": 0.20,
        "labour_fit_column": "accommodation_food_labour_pct",
    },
    {
        "category": "Health and Wellness",
        "subcategory": "Fitness Center",
        "avg_ticket": 58,
        "base_capture_rate": 0.0052,
        "gross_margin_pct": 0.55,
        "space_sqft": 7000,
        "monthly_staff_cost": 23000,
        "monthly_utilities": 5700,
        "competition_sensitivity": 0.56,
        "income_sensitivity": 0.72,
        "density_sensitivity": 0.62,
        "student_weight": 0.25,
        "young_adult_weight": 0.42,
        "family_weight": 0.22,
        "senior_weight": 0.08,
        "diversity_weight": 0.15,
        "immigrant_weight": 0.15,
        "labour_fit_column": "other_services_labour_pct",
    },
    {
        "category": "Health and Wellness",
        "subcategory": "Yoga Studio",
        "avg_ticket": 72,
        "base_capture_rate": 0.0042,
        "gross_margin_pct": 0.60,
        "space_sqft": 1800,
        "monthly_staff_cost": 11500,
        "monthly_utilities": 2000,
        "competition_sensitivity": 0.45,
        "income_sensitivity": 0.78,
        "density_sensitivity": 0.70,
        "student_weight": 0.14,
        "young_adult_weight": 0.48,
        "family_weight": 0.20,
        "senior_weight": 0.12,
        "diversity_weight": 0.18,
        "immigrant_weight": 0.12,
        "labour_fit_column": "other_services_labour_pct",
    },
    {
        "category": "Personal Care",
        "subcategory": "Barbershop",
        "avg_ticket": 32,
        "base_capture_rate": 0.0068,
        "gross_margin_pct": 0.62,
        "space_sqft": 1100,
        "monthly_staff_cost": 12000,
        "monthly_utilities": 1500,
        "competition_sensitivity": 0.54,
        "income_sensitivity": 0.35,
        "density_sensitivity": 0.64,
        "student_weight": 0.16,
        "young_adult_weight": 0.36,
        "family_weight": 0.28,
        "senior_weight": 0.12,
        "diversity_weight": 0.24,
        "immigrant_weight": 0.20,
        "labour_fit_column": "other_services_labour_pct",
    },
    {
        "category": "Personal Care",
        "subcategory": "Nail Salon",
        "avg_ticket": 45,
        "base_capture_rate": 0.0055,
        "gross_margin_pct": 0.63,
        "space_sqft": 1200,
        "monthly_staff_cost": 12500,
        "monthly_utilities": 1650,
        "competition_sensitivity": 0.55,
        "income_sensitivity": 0.55,
        "density_sensitivity": 0.66,
        "student_weight": 0.14,
        "young_adult_weight": 0.42,
        "family_weight": 0.25,
        "senior_weight": 0.08,
        "diversity_weight": 0.22,
        "immigrant_weight": 0.18,
        "labour_fit_column": "other_services_labour_pct",
    },
    {
        "category": "Personal Care",
        "subcategory": "Hair Salon",
        "avg_ticket": 62,
        "base_capture_rate": 0.005,
        "gross_margin_pct": 0.64,
        "space_sqft": 1300,
        "monthly_staff_cost": 13500,
        "monthly_utilities": 1800,
        "competition_sensitivity": 0.55,
        "income_sensitivity": 0.55,
        "density_sensitivity": 0.62,
        "student_weight": 0.12,
        "young_adult_weight": 0.36,
        "family_weight": 0.28,
        "senior_weight": 0.14,
        "diversity_weight": 0.18,
        "immigrant_weight": 0.15,
        "labour_fit_column": "other_services_labour_pct",
    },
    {
        "category": "Specialty Retail",
        "subcategory": "Clothing Boutique",
        "avg_ticket": 68,
        "base_capture_rate": 0.0038,
        "gross_margin_pct": 0.52,
        "space_sqft": 1600,
        "monthly_staff_cost": 10500,
        "monthly_utilities": 1800,
        "competition_sensitivity": 0.58,
        "income_sensitivity": 0.70,
        "density_sensitivity": 0.62,
        "student_weight": 0.12,
        "young_adult_weight": 0.42,
        "family_weight": 0.28,
        "senior_weight": 0.10,
        "diversity_weight": 0.25,
        "immigrant_weight": 0.15,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Specialty Retail",
        "subcategory": "Pet Supply Store",
        "avg_ticket": 46,
        "base_capture_rate": 0.0045,
        "gross_margin_pct": 0.44,
        "space_sqft": 2200,
        "monthly_staff_cost": 11000,
        "monthly_utilities": 2100,
        "competition_sensitivity": 0.45,
        "income_sensitivity": 0.52,
        "density_sensitivity": 0.50,
        "student_weight": 0.08,
        "young_adult_weight": 0.22,
        "family_weight": 0.50,
        "senior_weight": 0.16,
        "diversity_weight": 0.10,
        "immigrant_weight": 0.08,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Specialty Retail",
        "subcategory": "Electronics Repair Shop",
        "avg_ticket": 95,
        "base_capture_rate": 0.0028,
        "gross_margin_pct": 0.56,
        "space_sqft": 900,
        "monthly_staff_cost": 9000,
        "monthly_utilities": 1350,
        "competition_sensitivity": 0.38,
        "income_sensitivity": 0.45,
        "density_sensitivity": 0.60,
        "student_weight": 0.22,
        "young_adult_weight": 0.42,
        "family_weight": 0.22,
        "senior_weight": 0.10,
        "diversity_weight": 0.20,
        "immigrant_weight": 0.18,
        "labour_fit_column": "retail_trade_labour_pct",
    },
    {
        "category": "Professional and Local Services",
        "subcategory": "Accounting Office",
        "avg_ticket": 220,
        "base_capture_rate": 0.0013,
        "gross_margin_pct": 0.74,
        "space_sqft": 1200,
        "monthly_staff_cost": 15500,
        "monthly_utilities": 1350,
        "competition_sensitivity": 0.35,
        "income_sensitivity": 0.65,
        "density_sensitivity": 0.45,
        "student_weight": 0.05,
        "young_adult_weight": 0.22,
        "family_weight": 0.42,
        "senior_weight": 0.22,
        "diversity_weight": 0.12,
        "immigrant_weight": 0.18,
        "labour_fit_column": "other_services_labour_pct",
    },
    {
        "category": "Professional and Local Services",
        "subcategory": "Tutoring Centre",
        "avg_ticket": 38,
        "base_capture_rate": 0.0045,
        "gross_margin_pct": 0.66,
        "space_sqft": 1500,
        "monthly_staff_cost": 12500,
        "monthly_utilities": 1600,
        "competition_sensitivity": 0.40,
        "income_sensitivity": 0.60,
        "density_sensitivity": 0.52,
        "student_weight": 0.40,
        "young_adult_weight": 0.18,
        "family_weight": 0.50,
        "senior_weight": 0.04,
        "diversity_weight": 0.22,
        "immigrant_weight": 0.25,
        "labour_fit_column": "other_services_labour_pct",
    },
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_num(row: pd.Series, col: str, default: float = 0.0) -> float:
    val = row.get(col, default)
    if pd.isna(val):
        return default
    return float(val)


def normalize_pct(value: float) -> float:
    return clamp(value / 100.0, 0.0, 1.0)


def impute_city_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    for col in numeric_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].median())
    return df


def radius_population_factor(radius_km: float) -> float:
    factors = {
        1: 0.24,
        3: 0.52,
        5: 0.78,
        10: 1.00,
    }
    return factors.get(int(radius_km), min(1.0, 0.13 * radius_km))


def estimate_lease_cost(row: pd.Series, profile: Dict[str, object], radius_km: float, rng: np.random.Generator) -> float:
    rent_index = safe_num(row, "rent_cost_index_0_100", 50) / 100
    density_index = safe_num(row, "density_index_0_100", 50) / 100

    # V2: less aggressive lease estimate than V1.
    base_price_per_sqft_year = 14 + (rent_index * 22) + (density_index * 7)
    radius_discount = {1: 1.04, 3: 1.01, 5: 0.98, 10: 0.92}.get(int(radius_km), 1.0)

    sqft = float(profile["space_sqft"])
    annual_lease = base_price_per_sqft_year * sqft * radius_discount
    monthly_lease = annual_lease / 12

    noise = rng.normal(1.0, 0.07)
    return round(max(750, monthly_lease * noise), 2)


def estimate_competition(row: pd.Series, profile: Dict[str, object], radius_km: float, rng: np.random.Generator) -> Dict[str, float]:
    density_idx = safe_num(row, "density_index_0_100", 50) / 100
    market_idx = safe_num(row, "market_base_index_0_100", 50) / 100
    relevant_labour_pct = safe_num(row, str(profile["labour_fit_column"]), 5)

    category_factor = relevant_labour_pct / 10.0
    radius_factor = math.sqrt(radius_km)

    # V2: slightly lower competitor expectation and gentler saturation.
    expected_competitors = (1.5 + 12 * density_idx + 7 * market_idx + 5 * category_factor) * radius_factor
    competitor_count = max(0, int(rng.poisson(max(0.35, expected_competitors))))

    population = safe_num(row, "population_2021", 10000)
    competitor_density = competitor_count / max(1, population / 10000)

    saturation_score = clamp(
        (competitor_density / 10.0) * 100 * float(profile["competition_sensitivity"]),
        0,
        100,
    )

    return {
        "competitor_count": competitor_count,
        "competitor_density_per_10k": round(competitor_density, 3),
        "competition_score_0_100": round(saturation_score, 2),
    }


def demographic_fit_score(row: pd.Series, profile: Dict[str, object]) -> float:
    student = normalize_pct(safe_num(row, "youth_15_24_pct", 0))
    young_adult = normalize_pct(safe_num(row, "young_adult_20_34_pct", 0))
    family = normalize_pct(safe_num(row, "family_with_children_pct", 0))
    senior = normalize_pct(safe_num(row, "seniors_65_plus_pct", 0))
    diversity = safe_num(row, "diversity_index_0_100", 0) / 100
    immigrant = normalize_pct(safe_num(row, "immigrant_pct", 0))

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


def demand_score(row: pd.Series, profile: Dict[str, object], competition_score: float, rng: np.random.Generator) -> float:
    demo_fit = demographic_fit_score(row, profile)
    income_idx = safe_num(row, "income_index_0_100", 50)
    density_idx = safe_num(row, "density_index_0_100", 50)
    market_idx = safe_num(row, "market_base_index_0_100", 50)
    employment = safe_num(row, "employment_rate_pct", 55)

    income_component = income_idx * float(profile["income_sensitivity"])
    density_component = density_idx * float(profile["density_sensitivity"])

    # V2: demand is less punished by competition and has a moderate baseline.
    raw = (
        12
        + demo_fit * 0.32
        + market_idx * 0.23
        + income_component * 0.14
        + density_component * 0.13
        + employment * 0.12
        - competition_score * 0.10
    )

    noise = rng.normal(0, 4.5)
    return round(clamp(raw + noise, 0, 100), 2)


def risk_class(score: float) -> str:
    # V2: thresholds tuned to reduce excessive high-risk skew.
    if score < 42:
        return "low"
    if score < 68:
        return "medium"
    return "high"


def indicator_from_score(score: float, reverse: bool = False) -> str:
    if reverse:
        if score < 42:
            return "green"
        if score < 68:
            return "yellow"
        return "red"

    if score >= 68:
        return "green"
    if score >= 42:
        return "yellow"
    return "red"


def generate_scenarios(city_df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    rows = []
    scenario_id = 1

    for _, city in city_df.iterrows():
        for profile in BUSINESS_TAXONOMY:
            for radius in RADII_KM:
                if len(rows) >= MAX_ROWS:
                    break

                reachable_population = safe_num(city, "population_2021", 0) * radius_population_factor(radius)
                reachable_population = max(1, reachable_population)

                competition = estimate_competition(city, profile, radius, rng)
                demo_fit = demographic_fit_score(city, profile)
                demand = demand_score(city, profile, competition["competition_score_0_100"], rng)

                base_capture = float(profile["base_capture_rate"])
                capture_multiplier = clamp(0.72 + (demand / 115), 0.35, 1.70)

                # V2: softer competition penalty.
                competition_penalty = 1 - (competition["competition_score_0_100"] / 100) * 0.24
                demand_multiplier = clamp(capture_multiplier * competition_penalty, 0.22, 1.80)

                customers_per_day = reachable_population * base_capture * demand_multiplier
                customers_per_day *= rng.normal(1.0, 0.10)
                customers_per_day = max(1, customers_per_day)

                avg_ticket = float(profile["avg_ticket"]) * rng.normal(1.0, 0.06)
                gross_margin_pct = clamp(float(profile["gross_margin_pct"]) * rng.normal(1.0, 0.04), 0.15, 0.88)

                monthly_revenue = customers_per_day * avg_ticket * 30
                monthly_gross_profit = monthly_revenue * gross_margin_pct

                lease_cost = estimate_lease_cost(city, profile, radius, rng)
                staff_cost = float(profile["monthly_staff_cost"]) * rng.normal(1.0, 0.07)
                utilities_cost = float(profile["monthly_utilities"]) * rng.normal(1.0, 0.09)
                marketing_cost = max(600, monthly_revenue * rng.uniform(0.018, 0.045))
                other_fixed_cost = rng.uniform(700, 3200)

                monthly_operating_cost = lease_cost + staff_cost + utilities_cost + marketing_cost + other_fixed_cost
                monthly_net_revenue = monthly_gross_profit - monthly_operating_cost
                profit_margin_pct = (monthly_net_revenue / monthly_revenue) * 100 if monthly_revenue > 0 else -100

                lease_burden_score = clamp((lease_cost / max(monthly_revenue, 1)) * 150, 0, 100)
                low_demand_risk = 100 - demand
                competition_risk = competition["competition_score_0_100"]

                # V2: profit risk is less punishing. A small negative margin is not automatically catastrophic.
                profit_risk = clamp(45 - profit_margin_pct, 0, 100)
                rent_pressure = safe_num(city, "rent_pressure_index_0_100", 50)

                investment_risk_score = (
                    competition_risk * 0.18
                    + low_demand_risk * 0.25
                    + lease_burden_score * 0.16
                    + profit_risk * 0.22
                    + rent_pressure * 0.07
                    + 8
                )
                investment_risk_score = round(clamp(investment_risk_score + rng.normal(0, 4), 0, 100), 2)

                feasibility_score = round(clamp(
                    demand * 0.36
                    + (100 - competition_risk) * 0.18
                    + clamp(profit_margin_pct + 45, 0, 100) * 0.31
                    + (100 - rent_pressure) * 0.10
                    + demo_fit * 0.05,
                    0,
                    100,
                ), 2)

                # V2: recommendation thresholds are realistic but less overly strict.
                if feasibility_score >= 58 and investment_risk_score < 65:
                    recommendation = "recommended"
                elif feasibility_score >= 40 and investment_risk_score < 80:
                    recommendation = "borderline"
                else:
                    recommendation = "not_recommended"

                row = {
                    "scenario_id": scenario_id,
                    "municipality_name": city.get("municipality_name"),
                    "municipality_type": city.get("municipality_type"),
                    "geo_name_raw": city.get("geo_name_raw"),
                    "business_category": profile["category"],
                    "business_subcategory": profile["subcategory"],
                    "radius_km": radius,

                    "population_2021": round(safe_num(city, "population_2021", 0), 2),
                    "population_density_per_km2": round(safe_num(city, "population_density_per_km2", 0), 2),
                    "population_growth_2016_2021_pct": round(safe_num(city, "population_growth_2016_2021_pct", 0), 2),
                    "household_median_total_income_2020": round(safe_num(city, "household_median_total_income_2020", 0), 2),
                    "children_0_14_pct": round(safe_num(city, "children_0_14_pct", 0), 2),
                    "youth_15_24_pct": round(safe_num(city, "youth_15_24_pct", 0), 2),
                    "young_adult_20_34_pct": round(safe_num(city, "young_adult_20_34_pct", 0), 2),
                    "working_age_25_64_pct": round(safe_num(city, "working_age_25_64_pct", 0), 2),
                    "seniors_65_plus_pct": round(safe_num(city, "seniors_65_plus_pct", 0), 2),
                    "family_with_children_pct": round(safe_num(city, "family_with_children_pct", 0), 2),
                    "employment_rate_pct": round(safe_num(city, "employment_rate_pct", 0), 2),
                    "unemployment_rate_pct": round(safe_num(city, "unemployment_rate_pct", 0), 2),
                    "immigrant_pct": round(safe_num(city, "immigrant_pct", 0), 2),
                    "visible_minority_pct": round(safe_num(city, "visible_minority_pct", 0), 2),
                    "diversity_index_0_100": round(safe_num(city, "diversity_index_0_100", 0), 2),
                    "renter_pct": round(safe_num(city, "renter_pct", 0), 2),
                    "renter_average_monthly_shelter_cost": round(safe_num(city, "renter_average_monthly_shelter_cost", 0), 2),
                    "rent_pressure_index_0_100": round(safe_num(city, "rent_pressure_index_0_100", 0), 2),
                    "market_base_index_0_100": round(safe_num(city, "market_base_index_0_100", 0), 2),

                    "average_ticket_size": round(avg_ticket, 2),
                    "base_capture_rate": round(base_capture, 6),
                    "gross_margin_pct": round(gross_margin_pct * 100, 2),
                    "estimated_space_sqft": float(profile["space_sqft"]),

                    "reachable_population_estimate": round(reachable_population, 2),
                    "demographic_fit_score_0_100": demo_fit,
                    "demand_score_0_100": demand,
                    "competitor_count_estimate": competition["competitor_count"],
                    "competitor_density_per_10k": competition["competitor_density_per_10k"],
                    "competition_score_0_100": competition["competition_score_0_100"],
                    "monthly_lease_cost_estimate": round(lease_cost, 2),
                    "monthly_staff_cost_estimate": round(staff_cost, 2),
                    "monthly_utilities_cost_estimate": round(utilities_cost, 2),
                    "monthly_marketing_cost_estimate": round(marketing_cost, 2),
                    "monthly_operating_cost_estimate": round(monthly_operating_cost, 2),

                    "expected_customers_per_day": round(customers_per_day, 2),
                    "monthly_gross_revenue_estimate": round(monthly_revenue, 2),
                    "monthly_net_revenue_estimate": round(monthly_net_revenue, 2),
                    "profit_margin_pct": round(profit_margin_pct, 2),
                    "feasibility_score_0_100": feasibility_score,
                    "investment_risk_score_0_100": investment_risk_score,
                    "investment_risk_class": risk_class(investment_risk_score),
                    "recommendation_label": recommendation,
                    "demand_indicator": indicator_from_score(demand),
                    "competition_indicator": indicator_from_score(competition["competition_score_0_100"], reverse=True),
                    "risk_indicator": indicator_from_score(investment_risk_score, reverse=True),
                }

                rows.append(row)
                scenario_id += 1

    return pd.DataFrame(rows)


def create_dictionary(columns: List[str]) -> pd.DataFrame:
    descriptions = {
        "scenario_id": "Unique generated scenario identifier.",
        "municipality_name": "Ontario municipality used for the scenario.",
        "business_category": "Broad business category.",
        "business_subcategory": "Specific business type.",
        "radius_km": "Scenario analysis radius.",
        "reachable_population_estimate": "Estimated reachable population based on radius.",
        "demographic_fit_score_0_100": "How well the local demographics fit the business type.",
        "demand_score_0_100": "Estimated local demand strength.",
        "competition_score_0_100": "Estimated competition and market saturation pressure.",
        "monthly_lease_cost_estimate": "Synthetic commercial lease estimate.",
        "monthly_operating_cost_estimate": "Synthetic monthly operating cost estimate.",
        "expected_customers_per_day": "Generated target estimate for daily customers.",
        "monthly_gross_revenue_estimate": "Generated target estimate for monthly gross revenue.",
        "monthly_net_revenue_estimate": "Generated target estimate for monthly net revenue.",
        "feasibility_score_0_100": "Generated business feasibility score.",
        "investment_risk_score_0_100": "Generated target risk score.",
        "investment_risk_class": "Generated risk class label.",
        "recommendation_label": "Generated final recommendation label.",
    }

    return pd.DataFrame([
        {
            "column_name": col,
            "description": descriptions.get(col, "Scenario feature or generated label used by Zonalyze."),
        }
        for col in columns
    ])


def main() -> None:
    if not DEFAULT_INPUT.exists():
        raise FileNotFoundError(
            f"Input file not found: {DEFAULT_INPUT}. "
            "Run select_zonalyze_features.py first."
        )

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    city_df = pd.read_csv(DEFAULT_INPUT)
    city_df = impute_city_features(city_df)

    scenarios = generate_scenarios(city_df)

    scenario_path = DEFAULT_OUTPUT_DIR / OUTPUT_SCENARIOS
    taxonomy_path = DEFAULT_OUTPUT_DIR / OUTPUT_TAXONOMY
    dictionary_path = DEFAULT_OUTPUT_DIR / OUTPUT_DICTIONARY

    scenarios.to_csv(scenario_path, index=False)
    pd.DataFrame(BUSINESS_TAXONOMY).to_csv(taxonomy_path, index=False)
    create_dictionary(scenarios.columns.tolist()).to_csv(dictionary_path, index=False)

    print("Synthetic scenario generation complete.")
    print(f"Rows created: {len(scenarios)}")
    print(f"Columns created: {len(scenarios.columns)}")
    print(f"Scenario dataset: {scenario_path}")
    print(f"Business taxonomy seed: {taxonomy_path}")
    print(f"Dataset dictionary: {dictionary_path}")

    print("\nRisk class distribution:")
    print(scenarios["investment_risk_class"].value_counts().to_string())

    print("\nRecommendation distribution:")
    print(scenarios["recommendation_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
