from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import List

from app.schemas.geospatial import FootfallHeatmapPoint


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "market" / "observed_footfall_counts.csv"


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0088
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = lat2_rad - lat1_rad
    delta_lng = math.radians(lng2 - lng1)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def build_footfall_heatmap_points(
    *, center_lat: float, center_lng: float, radius_km: float
) -> List[FootfallHeatmapPoint]:
    """Return only observed municipal pedestrian counters inside the analysis radius."""
    if not DATA_PATH.exists():
        return []

    rows: list[dict[str, str]] = []
    with DATA_PATH.open(encoding="utf-8", newline="") as source_file:
        for row in csv.DictReader(source_file):
            try:
                latitude = float(row["latitude"])
                longitude = float(row["longitude"])
                observed_count = float(row["observed_count"])
            except (KeyError, TypeError, ValueError):
                continue
            if observed_count <= 0:
                continue
            if _distance_km(center_lat, center_lng, latitude, longitude) <= radius_km:
                rows.append(row)

    if not rows:
        return []

    max_count_by_unit = {
        unit: max(
            float(row["observed_count"])
            for row in rows
            if row["observed_unit"] == unit
        )
        for unit in {row["observed_unit"] for row in rows}
    }
    return [
        FootfallHeatmapPoint(
            point_id=f"observed-counter-{row['municipality'].lower()}-{row['site_id']}",
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            intensity=max(
                0.18,
                math.sqrt(
                    float(row["observed_count"])
                    / max_count_by_unit[row["observed_unit"]]
                ),
            ),
            evidence_type="observed_pedestrian_count",
            source=row["source"],
            label=row["label"],
            category="Municipal pedestrian counter",
            observed_count=float(row["observed_count"]),
            observed_unit=row["observed_unit"],
            observation_period=row["observation_period"],
            source_url=row["source_url"],
        )
        for row in rows
    ]
