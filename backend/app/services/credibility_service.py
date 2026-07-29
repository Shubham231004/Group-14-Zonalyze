from typing import Any, Dict, List

from app.schemas.dashboard import OutputEvidenceItem, PredictionCredibilityResponse


OBSERVED_CENSUS_FIELDS = [
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
]


def _item(
    field_name: str,
    label: str,
    method: str,
    credibility: str,
    source: str,
    user_note: str,
) -> OutputEvidenceItem:
    return OutputEvidenceItem(
        field_name=field_name,
        label=label,
        method=method,
        credibility=credibility,
        source=source,
        user_note=user_note,
    )


def _risk_model_signal(prediction_result: Dict[str, Any]) -> float:
    probabilities = prediction_result.get("risk_probabilities") or {}
    if not probabilities:
        return 45.0

    highest_probability = max(float(value) for value in probabilities.values())
    return round(max(35.0, min(95.0, highest_probability * 100)), 2)


def _data_quality_score(features: Dict[str, Any]) -> float:
    present = 0
    for field in OBSERVED_CENSUS_FIELDS:
        value = features.get(field)
        if value is not None and value != "" and float(value) >= 0:
            present += 1

    completeness = present / len(OBSERVED_CENSUS_FIELDS)
    return round(completeness * 100, 2)


def _proxy_dependency_score(features: Dict[str, Any]) -> float:
    """
    Higher score means lower dependence on unsupported assumptions.

    Step 9 reduced proxy dependency when a competition observation catalog row
    exists. Step 10 also reduces proxy dependency when a lease evidence row is
    present. Demand, staffing, and operating costs are still estimated, so the
    score remains intentionally cautious.
    """
    proxy_fields = [
        "monthly_lease_cost_estimate",
        "monthly_staff_cost_estimate",
        "monthly_utilities_cost_estimate",
        "monthly_operating_cost_estimate",
        "demand_score_0_100",
        "base_capture_rate",
    ]

    populated_proxy_fields = sum(
        1
        for field in proxy_fields
        if features.get(field) is not None and features.get(field) != ""
    )

    competition_is_catalog_backed = (
        features.get("competition_data_source")
        and features.get("competition_data_source") != "feature_builder_proxy"
    )

    lease_is_catalog_backed = (
        features.get("lease_data_method")
        and features.get("lease_data_method") != "feature_fallback_proxy"
    )

    demand_is_catalog_backed = (
        features.get("demand_data_method")
        and features.get("demand_data_method") != "feature_fallback_proxy"
    )

    raw = 82.0 - populated_proxy_fields * 4.5
    if competition_is_catalog_backed:
        raw += 8.0
    else:
        raw -= 8.0

    if lease_is_catalog_backed:
        raw += 7.0
    else:
        raw -= 6.0

    if demand_is_catalog_backed:
        raw += 6.0
    else:
        raw -= 6.0

    return round(max(38.0, min(90.0, raw)), 2)


def _confidence_level(score: float) -> str:
    if score >= 80:
        return "strong"
    if score >= 65:
        return "moderate"
    if score >= 50:
        return "limited"
    return "experimental"


def build_prediction_credibility(
    features: Dict[str, Any],
    prediction_result: Dict[str, Any],
) -> PredictionCredibilityResponse:
    """
    Builds a transparent credibility profile for the current prediction.

    This does not pretend that every value is directly observed. It separates
    census-backed inputs, model outputs, proxy estimates, and derived metrics so
    users can understand how much trust to place in each part of the result.
    """
    data_quality = _data_quality_score(features)
    model_signal = _risk_model_signal(prediction_result)
    proxy_dependency = _proxy_dependency_score(features)

    overall = round(
        data_quality * 0.35 + model_signal * 0.35 + proxy_dependency * 0.30,
        2,
    )

    observed_inputs: List[OutputEvidenceItem] = [
        _item(
            "population_2021",
            "Population",
            "observed",
            "high",
            "Statistics Canada 2021 Census profile data processed for Ontario CSDs",
            "This value is grounded in an official demographic dataset.",
        ),
        _item(
            "household_median_total_income_2020",
            "Median household income",
            "observed",
            "high",
            "Statistics Canada 2021 Census profile data processed for Ontario CSDs",
            "This value is used as a purchasing-power signal, not as a direct revenue guarantee.",
        ),
        _item(
            "diversity_index_0_100",
            "Diversity index",
            "observed/engineered",
            "medium-high",
            "Engineered from census demographic composition fields",
            "The source fields are real census inputs, while the final index is derived for easier comparison.",
        ),
        _item(
            "employment_rate_pct",
            "Employment rate",
            "observed",
            "high",
            "Statistics Canada 2021 Census profile data processed for Ontario CSDs",
            "This is used as a local economic context signal.",
        ),
    ]

    model_predicted_outputs: List[OutputEvidenceItem] = [
        _item(
            "predicted_monthly_net_revenue",
            "Prototype monthly net revenue estimate",
            "model_predicted",
            "moderate",
            "Random forest regressor trained on simulation-generated business scenarios",
            "This is a prototype model output trained on simulation-generated labels. It should be treated as a planning estimate, not a validated revenue forecast.",
        ),
        _item(
            "predicted_risk_class",
            "Prototype investment risk estimate",
            "model_predicted",
            "moderate",
            "Random forest classifier trained on proxy risk labels",
            "The model predicts a prototype risk category within the current simulated training environment, not a validated real-world failure probability.",
        ),
        _item(
            "predicted_feasibility_score",
            "Prototype feasibility estimate",
            "model_predicted",
            "moderate",
            "Random forest regressor trained on proxy feasibility labels",
            "This should be used for comparison between scenarios, not as an objective feasibility truth.",
        ),
    ]

    derived_metrics: List[OutputEvidenceItem] = [
        _item(
            "population_density_per_km2",
            "Population density",
            "derived",
            "high",
            "Calculated from census population and land area",
            "This is a normal derived metric and is safer than a business outcome score.",
        ),
        _item(
            "reachable_population_estimate",
            "Reachable population estimate",
            "derived/proxy_estimated",
            "medium",
            "Calculated from municipality population and selected radius coverage factor",
            "This approximates coverage and should later use actual geospatial catchment boundaries.",
        ),
    ]

    competition_is_catalog_backed = (
        features.get("competition_data_source")
        and features.get("competition_data_source") != "feature_builder_proxy"
    )

    if competition_is_catalog_backed:
        observed_inputs.append(
            _item(
                "competitor_count_estimate",
                "Same-category competitor count",
                "catalog_observed/derived",
                str(features.get("competition_data_credibility", "medium")),
                str(features.get("competition_data_source", "Competition observation catalog")),
                "This value now comes from a replaceable competition observation catalog. The pressure index is still derived, but the count is no longer created only from demographic formulas.",
            )
        )
    
    proxy_estimated_inputs: List[OutputEvidenceItem] = []

    lease_is_catalog_backed = (
        features.get("lease_data_method")
        and features.get("lease_data_method") != "feature_fallback_proxy"
    )

    if lease_is_catalog_backed:
        observed_inputs.append(
            _item(
                "monthly_lease_cost_estimate",
                "Monthly lease cost range",
                "catalog_proxy_range",
                str(features.get("lease_data_credibility", "medium")),
                str(features.get("lease_data_source", "Lease cost evidence catalog")),
                "Lease is now represented as a range-backed evidence object. It is still not a verified commercial lease listing, but it is no longer hidden as one fixed calculation.",
            )
        )
        derived_metrics.append(
            _item(
                "lease_cost_per_sqft_year",
                "Lease cost per square foot",
                "derived_from_lease_evidence",
                "medium",
                str(features.get("lease_data_source", "Lease cost evidence catalog")),
                "This value is derived from the lease range and estimated space requirement. It should be calibrated with real listings later.",
            )
        )

    if not competition_is_catalog_backed:
        proxy_estimated_inputs.extend([
            _item(
                "competitor_count_estimate",
                "Estimated competitor count",
                "proxy_estimated",
                "limited",
                "Fallback estimate from population density, market base, business category, and labour-market signals",
                "No competition observation row was available for this scenario. Add OSM/Places/business directory data for stronger credibility.",
            ),
            _item(
                "competition_score_0_100",
                "Competition pressure estimate",
                "proxy_estimated",
                "limited",
                "Derived from fallback competitor estimate and competitor density",
                "This is not a directly observed market saturation measure yet.",
            ),
        ])
    else:
        derived_metrics.append(
            _item(
                "competition_score_0_100",
                "Competition pressure estimate estimate",
                "derived_from_catalog_observation",
                "medium",
                str(features.get("competition_data_source", "Competition observation catalog")),
                "The pressure index is calculated from observed same-category count, competitor density, and nearest competitor distance.",
            )
        )

    if not lease_is_catalog_backed:
        proxy_estimated_inputs.append(
            _item(
                "monthly_lease_cost_estimate",
                "Monthly lease cost estimate",
                "proxy_estimated",
                "limited",
                "Estimated from rent pressure, density, and assumed business space requirements",
                "This should later be calibrated with commercial lease listings or broker/rental market data.",
            )
        )

    demand_is_catalog_backed = (
        features.get("demand_data_method")
        and features.get("demand_data_method") != "feature_fallback_proxy"
    )

    if demand_is_catalog_backed:
        observed_inputs.append(
            _item(
                "demand_score_0_100",
                "Demand pressure index",
                "catalog_proxy_signal",
                str(features.get("demand_data_credibility", "medium")),
                str(features.get("demand_data_source", "Demand evidence catalog")),
                "Demand is now represented through a visible evidence object using reachable population, demographic fit, activity, transit, and foot-traffic proxy signals.",
            )
        )
    else:
        proxy_estimated_inputs.append(
            _item(
                "demand_score_0_100",
                "Demand proxy index",
                "proxy_estimated",
                "limited",
                "Estimated from demographic fit, density, income, employment, and competition pressure",
                "This is a structured proxy for demand until real foot traffic or transaction data is available.",
            )
        )

    return PredictionCredibilityResponse(
        overall_confidence_score=overall,
        confidence_level=_confidence_level(overall),
        data_quality_score=data_quality,
        model_signal_score=model_signal,
        proxy_dependency_score=proxy_dependency,
        observed_inputs=observed_inputs,
        model_predicted_outputs=model_predicted_outputs,
        proxy_estimated_inputs=proxy_estimated_inputs,
        derived_metrics=derived_metrics,
        user_facing_disclaimer=(
            "Zonalyze currently combines official census inputs, competition, lease, and demand evidence catalog signals, engineered proxy signals, "
            "and models trained on simulation-generated labels. Results are useful for "
            "scenario comparison and prototype decision support, but they are not yet "
            "validated real-world forecasts."
        ),
        next_data_needed=[
            "Broader real business listing, OpenStreetMap POI, or commercial directory coverage for all municipality/business combinations",
            "Verified commercial lease listings, broker data, or municipal commercial vacancy/rent datasets for location-specific rent calibration",
            "Observed business performance or closure/survival data for true risk labels",
            "Verified foot traffic, transit, mobility, or transaction data for stronger demand calibration",
            "Historical local business revenue benchmarks by industry where legally available",
        ],
    )
