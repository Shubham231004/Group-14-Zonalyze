from datetime import datetime, timezone

from app.models.demographics import DemographicZone
from app.schemas.scenario import AnalyzeScenarioRequest
from app.schemas.sensor_packet import MetricItem, SensorPacket
from app.sensors.base_sensor import BaseSensor


class PeopleLocationSensor(BaseSensor):
    def __init__(self):
        super().__init__(
            device_name="people_location_monitor",
            sensor_type="people_location",
        )

    def compute(
        self,
        request: AnalyzeScenarioRequest,
        demographic_row: DemographicZone,
    ) -> SensorPacket:
        return SensorPacket(
            timestamp=datetime.now(timezone.utc),
            device_name=self.device_name,
            sensor_type=self.sensor_type,
            selected_zone=request.municipality_name,
            selected_business_type=request.business_subcategory,
            radius_km=request.radius_km,
            indicator=demographic_row.indicator,
            summary_text=demographic_row.summary_text,
            metrics=[
                MetricItem(
                    key="population_total",
                    label="Total Population",
                    value=demographic_row.base_population,
                    unit="people",
                ),
                MetricItem(
                    key="students_pct",
                    label="Youth / Student-Age Population",
                    value=demographic_row.students_pct,
                    unit="%",
                ),
                MetricItem(
                    key="families_pct",
                    label="Families",
                    value=demographic_row.families_pct,
                    unit="%",
                ),
                MetricItem(
                    key="retirees_pct",
                    label="Retirees / Seniors",
                    value=demographic_row.retirees_pct,
                    unit="%",
                ),
            ],
            meta={
                "data_source": "postgresql",
                "status": "active",
            },
        )
