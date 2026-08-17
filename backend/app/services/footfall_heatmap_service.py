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
    rows: list[dict[str, str]] = []
    # The counter dataset is real municipal open data, not shipped in git (like the
    # other observation seeds under data/market/) — treat "not deployed yet" the same
    # as "no counters in this radius" rather than crashing the request.
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open(encoding="utf-8", newline="") as source_file:
        for row in csv.DictReader(source_file):
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])
            if _distance_km(center_lat, center_lng, latitude, longitude) <= radius_km:
                rows.append(row)

    if not rows:
        return []

    max_count = max(float(row["observed_count"]) for row in rows)
    return [
        FootfallHeatmapPoint(
            point_id=f"observed-counter-{row['municipality'].lower()}-{row['site_id']}",
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            intensity=max(0.18, math.sqrt(float(row["observed_count"]) / max_count)),
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
