"""
Shared Zonalyze scenario feature pipeline.

This module is the SINGLE source of truth for how a (municipality, business,
radius) scenario is turned into the numeric feature row the ML models consume.

Both the training-dataset generator (app/ml/generate_training_dataset.py) and the
runtime inference builder (app/ml/scenario_feature_builder.py) call
`build_scenario_record` so that the model always sees inputs shaped exactly like
its training data. Previously training and inference used two different, drifting
formula sets, which made every runtime prediction collapse to a near-constant
"guaranteed loss" result. Keeping one function removes that train/inference skew.

Determinism:
- Pass `rng=None` (inference) to get a deterministic point estimate: all random
  noise is 0, and random draws (operating days, cost multipliers, etc.) use their
  expected value.
- Pass a numpy Generator (training) to sample realistic variation around the same
  formulas so the models learn robust relationships.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


# --------------------------------------------------------------------------- #
# Small numeric helpers
# --------------------------------------------------------------------------- #
def bounded(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return number


def _noise(rng: Optional[np.random.Generator], scale: float) -> float:
    """Gaussian noise for training, exactly 0 for deterministic inference."""
    if rng is None or scale <= 0:
        return 0.0
    return float(rng.normal(0.0, scale))


def _uniform(rng: Optional[np.random.Generator], low: float, high: float) -> float:
    """Sampled uniform for training, midpoint for deterministic inference."""
    if rng is None:
        return (low + high) / 2.0
    return float(rng.uniform(low, high))


def _choice(rng: Optional[np.random.Generator], options, deterministic):
    if rng is None:
        return deterministic
    return type(deterministic)(rng.choice(options))


# --------------------------------------------------------------------------- #
# Normalized scenario inputs
# --------------------------------------------------------------------------- #
@dataclass
class MunicipalitySignals:
    municipality_name: str
    municipality_type: str
    population_2021: float
    population_density: float
    median_income: float
    median_age: float
    household_count: float
    employment_rate: float
    diversity_index: float
    students_pct: float
    families_pct: float
    retirees_pct: float
    immigrant_pct: float
    visible_minority_pct: float
    income_index: float
    density_index: float
    market_base_index: float
    rent_cost_index: float


@dataclass
class BusinessProfile:
    subcategory: str
    group: str
    avg_ticket: float
    space_sqft: float
    base_capture_rate: float
    repeat_customer_factor: float
    operating_cost_multiplier: float
    competition_sensitivity: float
    lease_sensitivity: float
    demand_sensitivity: float


# Column mapping from the census "selected features" CSV to MunicipalitySignals.
def municipality_signals_from_census_row(row: Dict[str, Any]) -> MunicipalitySignals:
    """Build normalized municipality signals from one census CSV row.

    `row` may be a pandas Series or a plain dict. All real per-municipality
    census signals are used directly (income, age, diversity, employment, the
    precomputed 0-100 indices), so predictions become genuinely sensitive to how
    municipalities actually differ.
    """
    def g(key: str, default: float = 0.0) -> float:
        return _to_float(row.get(key) if hasattr(row, "get") else row[key], default)

    population = g("population_2021")
    avg_household_size = g("average_household_size", 0.0)
    household_count = population / avg_household_size if avg_household_size > 0 else population / 2.5

    name = str((row.get("municipality_name") if hasattr(row, "get") else row["municipality_name"]) or "").strip()
    muni_type = str((row.get("municipality_type") if hasattr(row, "get") else row.get("municipality_type", "")) or "").strip()

    return MunicipalitySignals(
        municipality_name=name,
        municipality_type=muni_type,
        population_2021=population,
        population_density=g("population_density_per_km2"),
        median_income=g("household_median_total_income_2020", 85000.0) or 85000.0,
        median_age=g("median_age", 39.0) or 39.0,
        household_count=household_count,
        employment_rate=g("employment_rate_pct", 60.0) or 60.0,
        diversity_index=g("diversity_index_0_100", 40.0),
        students_pct=g("youth_15_24_pct", 12.0),
        families_pct=g("family_with_children_pct", 40.0),
        retirees_pct=g("seniors_65_plus_pct", 16.0),
        immigrant_pct=g("immigrant_pct", 20.0),
        visible_minority_pct=g("visible_minority_pct", 20.0),
        income_index=bounded(g("income_index_0_100", 50.0), 5.0, 100.0),
        density_index=bounded(g("density_index_0_100", 50.0), 5.0, 100.0),
        market_base_index=bounded(g("market_base_index_0_100", 50.0), 0.0, 100.0),
        rent_cost_index=bounded(g("rent_cost_index_0_100", 50.0), 0.0, 100.0),
    )


def normalize_business_profile(config: Dict[str, Any]) -> BusinessProfile:
    """Normalize a raw business catalog entry into the numeric assumptions the
    feature pipeline needs. Mirrors the older _catalog_record defaults so retrained
    models stay compatible with the shared catalog."""
    subcategory = str(
        config.get("subcategory")
        or config.get("business_subcategory")
        or config.get("name")
        or "General Business"
    )
    group = str(config.get("category") or config.get("business_group") or "General Local Business")

    return BusinessProfile(
        subcategory=subcategory,
        group=group,
        avg_ticket=_to_float(config.get("avg_ticket"), 20.0),
        space_sqft=_to_float(config.get("space_sqft"), 1500.0),
        base_capture_rate=_to_float(
            config.get("base_capture_rate", config.get("target_customer_rate")), 0.0025
        ),
        repeat_customer_factor=_to_float(config.get("repeat_customer_factor"), 1.0),
        operating_cost_multiplier=_to_float(config.get("operating_cost_multiplier"), 1.0),
        competition_sensitivity=_to_float(config.get("competition_sensitivity"), 1.0),
        lease_sensitivity=_to_float(config.get("lease_sensitivity"), 1.0),
        demand_sensitivity=_to_float(config.get("demand_sensitivity"), 0.65),
    )


def _risk_class_from_score(score: float) -> str:
    if score < 48:
        return "low"
    if score < 70:
        return "medium"
    return "high"


# --------------------------------------------------------------------------- #
# Core: derive one full scenario record (features + training targets)
# --------------------------------------------------------------------------- #
def build_scenario_record(
    muni: MunicipalitySignals,
    biz: BusinessProfile,
    radius_km: float,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, Any]:
    """Derive the full feature row (and simulation training targets) for one
    scenario. Deterministic when rng is None (inference), sampled when rng is a
    numpy Generator (training)."""
    radius_km = float(radius_km)
    radius_factor = math.sqrt(radius_km / 5.0)

    avg_ticket_size = _uniform(rng, biz.avg_ticket * 0.75, biz.avg_ticket * 1.25) if rng is not None else biz.avg_ticket
    estimated_space_sqft = _uniform(rng, biz.space_sqft * 0.80, biz.space_sqft * 1.20) if rng is not None else biz.space_sqft

    reachable_population = bounded(
        muni.population_2021 * min(1.0, (radius_km / 8.0) ** 1.22),
        250.0,
        max(250.0, muni.population_2021),
    )

    if rng is not None:
        target_customer_rate = bounded(
            rng.normal(biz.base_capture_rate, biz.base_capture_rate * 0.20), 0.005, 0.20
        )
    else:
        target_customer_rate = bounded(biz.base_capture_rate, 0.005, 0.20)
    target_customer_pool = reachable_population * target_customer_rate * biz.repeat_customer_factor

    income_index = muni.income_index
    density_index = muni.density_index

    business_name = biz.subcategory.lower()
    demographic_fit = 50.0
    demographic_fit += muni.students_pct * (0.75 if any(k in business_name for k in ["coffee", "bubble", "tutoring", "pizza"]) else 0.20)
    demographic_fit += muni.families_pct * (0.55 if any(k in business_name for k in ["grocery", "daycare", "pharmacy", "dental"]) else 0.25)
    demographic_fit += muni.retirees_pct * (0.50 if any(k in business_name for k in ["pharmacy", "physiotherapy", "dental"]) else 0.10)
    demographic_fit += muni.diversity_index * (0.45 if any(k in business_name for k in ["indian", "chinese", "halal", "grocery"]) else 0.18)
    demographic_fit = bounded(demographic_fit / 1.85 + _noise(rng, 6), 5, 100)

    foot_traffic_proxy = bounded(0.48 * density_index + 0.30 * income_index + 0.22 * muni.employment_rate + _noise(rng, 10), 5, 100)
    transit_access_proxy = bounded(0.60 * density_index + 0.25 * muni.employment_rate + _noise(rng, 12), 5, 100)
    daytime_activity_index = bounded(0.50 * density_index + 0.35 * muni.employment_rate + 0.15 * foot_traffic_proxy + _noise(rng, 8), 5, 100)

    competitor_base = (reachable_population / 10000.0) * (0.65 + biz.competition_sensitivity)
    if rng is not None:
        competitor_count = int(max(0, rng.poisson(max(0.2, competitor_base))))
        nearest_competitor_distance = bounded(rng.gamma(1.8, 0.9) / max(0.35, radius_factor), 0.05, 15.0)
    else:
        competitor_count = int(round(competitor_base))
        # Expected value of gamma(shape=1.8, scale=0.9) is 1.62.
        nearest_competitor_distance = bounded(1.62 / max(0.35, radius_factor), 0.05, 15.0)
    competitor_density_per_10k = competitor_count / max(1.0, reachable_population / 10000.0)
    competition_pressure = bounded(
        competitor_density_per_10k * 14.0 * biz.competition_sensitivity
        + (20.0 / max(0.35, nearest_competitor_distance))
        + _noise(rng, 8),
        0,
        100,
    )

    base_psf = 18 + (density_index * 0.28) + (income_index * 0.16) + _noise(rng, 5)
    psf_year = bounded(base_psf * (0.75 + biz.lease_sensitivity * 0.65), 12, 85)
    median_monthly_lease = (psf_year * estimated_space_sqft) / 12.0
    lease_low = median_monthly_lease * _uniform(rng, 0.72, 0.88)
    lease_high = median_monthly_lease * _uniform(rng, 1.15, 1.45)
    rent_pressure = bounded((psf_year / 75.0) * 100.0 + biz.lease_sensitivity * 12 + _noise(rng, 5), 0, 100)

    demand_pressure = bounded(
        0.30 * demographic_fit
        + 0.25 * foot_traffic_proxy
        + 0.18 * daytime_activity_index
        + 0.15 * income_index
        + 0.12 * transit_access_proxy
        - 0.18 * competition_pressure * biz.competition_sensitivity
        + _noise(rng, 5),
        0,
        100,
    )

    expected_customers_per_day = bounded(
        (target_customer_pool / 24.0)
        * (0.55 + demand_pressure / 90.0)
        * (1.15 - competition_pressure / 260.0)
        * _uniform(rng, 0.85, 1.25),
        2,
        2500,
    )

    operating_days_per_month = _choice(rng, [24, 26, 28, 30], 28)
    gross_revenue = expected_customers_per_day * operating_days_per_month * avg_ticket_size

    staff_cost = (4500 + estimated_space_sqft * 1.25 + expected_customers_per_day * 32) * biz.operating_cost_multiplier
    utilities_cost = 600 + estimated_space_sqft * _uniform(rng, 0.25, 0.85)
    insurance_cost = _uniform(rng, 250, 900)
    marketing_cost = max(450, gross_revenue * _uniform(rng, 0.025, 0.075))
    inventory_or_supply_cost = gross_revenue * _uniform(rng, 0.22, 0.48)
    monthly_operating_cost = median_monthly_lease + staff_cost + utilities_cost + insurance_cost + marketing_cost + inventory_or_supply_cost
    monthly_net_revenue = gross_revenue - monthly_operating_cost

    lease_burden_ratio = median_monthly_lease / max(1.0, gross_revenue)
    profit_margin = monthly_net_revenue / max(1.0, gross_revenue)
    feasibility = bounded(
        54
        + profit_margin * 70
        + demand_pressure * 0.28
        + income_index * 0.10
        - competition_pressure * 0.20
        - rent_pressure * 0.16
        - max(0, lease_burden_ratio - 0.15) * 130
        + _noise(rng, 5),
        0,
        100,
    )

    profitability_signal = bounded((profit_margin + 0.20) / 0.55 * 100.0, 0, 100)
    lease_burden_signal = bounded(lease_burden_ratio / 0.45 * 100.0, 0, 100)
    negative_revenue_signal = bounded(max(0.0, -monthly_net_revenue) / 40000.0 * 100.0, 0, 100)
    risk_score = bounded(
        44
        + competition_pressure * 0.12
        + rent_pressure * 0.10
        + lease_burden_signal * 0.10
        + negative_revenue_signal * 0.10
        - demand_pressure * 0.18
        - profitability_signal * 0.26
        - feasibility * 0.18
        + _noise(rng, 12),
        0,
        100,
    )

    record: Dict[str, Any] = {
        # Categorical
        "municipality_name": muni.municipality_name,
        "business_subcategory": biz.subcategory,
        "business_group": biz.group,
        # Scenario
        "radius_km": round(radius_km, 2),
        # Municipality signals
        "population_2021": round(muni.population_2021, 2),
        "population_density": round(muni.population_density, 2),
        "median_income": round(muni.median_income, 2),
        "median_age": round(muni.median_age, 2),
        "household_count": round(muni.household_count, 2),
        "employment_rate": round(muni.employment_rate, 2),
        "diversity_index": round(muni.diversity_index, 2),
        "students_pct": round(muni.students_pct, 2),
        "families_pct": round(muni.families_pct, 2),
        "retirees_pct": round(muni.retirees_pct, 2),
        "immigrant_pct": round(muni.immigrant_pct, 2),
        "visible_minority_pct": round(muni.visible_minority_pct, 2),
        # Business assumptions
        "average_ticket_size": round(avg_ticket_size, 2),
        "estimated_space_sqft": round(estimated_space_sqft, 2),
        "target_customer_rate": round(target_customer_rate, 5),
        "lease_sensitivity": round(biz.lease_sensitivity, 3),
        "competition_sensitivity": round(biz.competition_sensitivity, 3),
        "demand_sensitivity": round(biz.demand_sensitivity, 3),
        # Derived market signals
        "reachable_population_estimate": round(reachable_population, 2),
        "target_customer_pool_estimate": round(target_customer_pool, 2),
        "demographic_fit_score": round(demographic_fit, 2),
        "foot_traffic_proxy_index": round(foot_traffic_proxy, 2),
        "transit_access_proxy_index": round(transit_access_proxy, 2),
        "daytime_activity_index": round(daytime_activity_index, 2),
        "competitor_count_same_type": competitor_count,
        "nearest_competitor_distance_km": round(nearest_competitor_distance, 3),
        "competitor_density_per_10k": round(competitor_density_per_10k, 3),
        "competition_score_0_100": round(competition_pressure, 2),
        "competition_pressure_index": round(competition_pressure, 2),
        "lease_cost_per_sqft_year": round(psf_year, 2),
        "low_monthly_lease_cost": round(lease_low, 2),
        "median_monthly_lease_cost": round(median_monthly_lease, 2),
        "high_monthly_lease_cost": round(lease_high, 2),
        "rent_pressure_index": round(rent_pressure, 2),
        "demand_pressure_index": round(demand_pressure, 2),
        "demand_score_0_100": round(demand_pressure, 2),
        "expected_customers_per_day": round(expected_customers_per_day, 2),
        "gross_revenue_monthly": round(gross_revenue, 2),
        "monthly_operating_cost_estimate": round(monthly_operating_cost, 2),
        "lease_burden_ratio": round(lease_burden_ratio, 4),
        "profit_margin_pct": round(profit_margin * 100.0, 2),
        # Simulation training targets (ignored at inference)
        "monthly_net_revenue": round(monthly_net_revenue, 2),
        "feasibility_score": round(feasibility, 2),
        "risk_score": round(risk_score, 2),
        "risk_class": _risk_class_from_score(risk_score),
        # Extra operating-cost components (display/evidence only, not model features)
        "monthly_staff_cost_estimate": round(staff_cost, 2),
        "monthly_utilities_cost_estimate": round(utilities_cost, 2),
        "monthly_marketing_cost_estimate": round(marketing_cost, 2),
        "monthly_insurance_cost_estimate": round(insurance_cost, 2),
        "monthly_inventory_supply_cost_estimate": round(inventory_or_supply_cost, 2),
    }
    return record


# Feature columns the models are trained on (order matters for reproducibility).
MODEL_FEATURE_COLUMNS = [
    "municipality_name",
    "business_subcategory",
    "business_group",
    "radius_km",
    "population_2021",
    "population_density",
    "median_income",
    "median_age",
    "household_count",
    "employment_rate",
    "diversity_index",
    "students_pct",
    "families_pct",
    "retirees_pct",
    "immigrant_pct",
    "visible_minority_pct",
    "average_ticket_size",
    "estimated_space_sqft",
    "target_customer_rate",
    "lease_sensitivity",
    "competition_sensitivity",
    "demand_sensitivity",
    "reachable_population_estimate",
    "target_customer_pool_estimate",
    "demographic_fit_score",
    "foot_traffic_proxy_index",
    "transit_access_proxy_index",
    "daytime_activity_index",
    "competitor_count_same_type",
    "nearest_competitor_distance_km",
    "competitor_density_per_10k",
    "competition_score_0_100",
    "competition_pressure_index",
    "lease_cost_per_sqft_year",
    "low_monthly_lease_cost",
    "median_monthly_lease_cost",
    "high_monthly_lease_cost",
    "rent_pressure_index",
    "demand_pressure_index",
    "demand_score_0_100",
    "expected_customers_per_day",
    "gross_revenue_monthly",
    "monthly_operating_cost_estimate",
    "lease_burden_ratio",
    "profit_margin_pct",
]

TARGET_COLUMNS = ["monthly_net_revenue", "risk_class", "feasibility_score", "risk_score"]
