import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.ml.scenario_feature_builder import build_prediction_features
from app.schemas.scenario import AnalyzeScenarioRequest
from app.schemas.sensor_packet import MetricItem, SensorPacket
from app.sensors.people_location_sensor import PeopleLocationSensor
from app.services.demographics_repository import find_matching_demographic_zone
from app.services.message_bus_service import publish_packet

logger = logging.getLogger(__name__)


def _safe_feature(features: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = features.get(key, default)
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def _census_backed_packet(request: AnalyzeScenarioRequest, sensor: PeopleLocationSensor) -> SensorPacket:
    """
    Builds a People & Location packet from the processed Census feature file.

    This is used when the older PostgreSQL demographic seed table does not have
    a row for the selected municipality. It keeps the dashboard useful for the
    newer Ontario municipality catalog.
    """
    features = build_prediction_features(
        municipality_name=request.municipality_name,
        business_subcategory=request.business_subcategory,
        radius_km=request.radius_km,
    )

    population = _safe_feature(features, "population_2021")
    density = _safe_feature(features, "population_density_per_km2")
    youth = _safe_feature(features, "youth_15_24_pct")
    families = _safe_feature(features, "family_with_children_pct")
    seniors = _safe_feature(features, "seniors_65_plus_pct")
    income = _safe_feature(features, "household_median_total_income_2020")
    diversity = _safe_feature(features, "diversity_index_0_100")
    employment = _safe_feature(features, "employment_rate_pct")
    renter_cost = _safe_feature(features, "renter_average_monthly_shelter_cost")

    demand_score = _safe_feature(features, "demand_score_0_100")
    if demand_score >= 65:
        indicator = "green"
    elif demand_score >= 40:
        indicator = "yellow"
    else:
        indicator = "red"

    packet = SensorPacket(
        timestamp=datetime.now(timezone.utc),
        device_name=sensor.device_name,
        sensor_type=sensor.sensor_type,
        selected_zone=request.municipality_name,
        selected_business_type=request.business_subcategory,
        radius_km=request.radius_km,
        indicator=indicator,
        summary_text=(
            f"{request.municipality_name} has a population base of {population:,.0f}, "
            f"a density of {density:,.1f} people/km², and a demand proxy index of "
            f"{demand_score:.1f}/100 for {request.business_subcategory}."
        ),
        metrics=[
            MetricItem(key="population_total", label="Total Population", value=population, unit="people"),
            MetricItem(key="population_density_per_km2", label="Population Density", value=density, unit="people/km²"),
            MetricItem(key="students_pct", label="Youth / Student-Age Population", value=youth, unit="%"),
            MetricItem(key="families_pct", label="Families with Children", value=families, unit="%"),
            MetricItem(key="retirees_pct", label="Seniors 65+", value=seniors, unit="%"),
            MetricItem(key="household_median_total_income_2020", label="Median Household Income", value=income, unit="CAD"),
            MetricItem(key="diversity_index_0_100", label="Diversity Index", value=diversity, unit="/100"),
            MetricItem(key="employment_rate_pct", label="Employment Rate", value=employment, unit="%"),
            MetricItem(key="renter_average_monthly_shelter_cost", label="Average Monthly Shelter Cost", value=renter_cost, unit="CAD"),
            MetricItem(key="demand_score_0_100", label="Demand Proxy Index", value=demand_score, unit="/100"),
        ],
        meta={
            "data_source": "statistics_canada_2021_processed_features",
            "status": "active",
        },
    )

    return packet


def get_people_location_packet(
    request: AnalyzeScenarioRequest,
    db: Session,
) -> SensorPacket:
    sensor = PeopleLocationSensor()

    row = find_matching_demographic_zone(
        db=db,
        selected_zone=request.municipality_name,
        radius_km=request.radius_km,
    )

    if row is not None:
        packet = sensor.compute(request, row)
        publish_packet(packet)
        return packet

    try:
        packet = _census_backed_packet(request, sensor)
        publish_packet(packet)
        return packet
    except Exception:
        # Log the full error server-side; do not leak internals to the client.
        logger.warning("Census-backed packet build failed for scenario", exc_info=True)
        fallback_packet = SensorPacket(
            timestamp=datetime.now(timezone.utc),
            device_name=sensor.device_name,
            sensor_type=sensor.sensor_type,
            selected_zone=request.municipality_name,
            selected_business_type=request.business_subcategory,
            radius_km=request.radius_km,
            indicator="red",
            summary_text="No demographic or census feature data is available for the selected scenario.",
            metrics=[],
            meta={
                "data_source": "none",
                "status": "missing",
            },
        )
        publish_packet(fallback_packet)
        return fallback_packet
