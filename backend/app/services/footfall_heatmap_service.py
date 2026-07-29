from __future__ import annotations

from typing import Any, Dict, Iterable, List
import math

from app.schemas.geospatial import FootfallHeatmapPoint


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except Exception:
        return None
    return None


def _point_from_poi(poi: Dict[str, Any], *, evidence_type: str, source: str) -> FootfallHeatmapPoint | None:
    lat = _safe_float(poi.get("latitude"))
    lng = _safe_float(poi.get("longitude"))
    if lat is None or lng is None:
        return None

    tags = poi.get("tags") or {}
    name = poi.get("name") or tags.get("name") or poi.get("category") or evidence_type
    osm_id = poi.get("osm_id")
    point_id = f"footfall-{evidence_type}-{osm_id or round(lat, 6)}-{round(lng, 6)}"

    return FootfallHeatmapPoint(
        point_id=str(point_id),
        latitude=round(lat, 6),
        longitude=round(lng, 6),
        intensity=1.0,
        evidence_type=evidence_type,
        source=source,
        label=str(name),
        osm_id=str(osm_id) if osm_id is not None else None,
        category=str(poi.get("category") or evidence_type),
    )


def build_footfall_heatmap_points(
    *,
    competitor_pois: Iterable[Dict[str, Any]],
    transit_pois: Iterable[Dict[str, Any]],
    commercial_activity_pois: Iterable[Dict[str, Any]],
    limit: int = 180,
) -> List[FootfallHeatmapPoint]:
    """Build a footfall-potential heatmap from real public OSM evidence points.

    This service does not create synthetic footfall values and does not estimate
    live pedestrian counts. Each heatmap point is backed by an OSM POI already
    returned by Overpass: competitor/business POIs, transit access points, or
    commercial activity POIs. Mapbox's heatmap renderer then visualizes density.
    """
    points: List[FootfallHeatmapPoint] = []
    seen: set[tuple[str, str, str]] = set()

    evidence_groups = [
        (competitor_pois, "business_poi", "OpenStreetMap business/competitor POI"),
        (transit_pois, "transit_access", "OpenStreetMap transit/access POI"),
        (commercial_activity_pois, "commercial_activity", "OpenStreetMap commercial activity POI"),
    ]

    for pois, evidence_type, source in evidence_groups:
        for poi in pois or []:
            point = _point_from_poi(poi, evidence_type=evidence_type, source=source)
            if not point:
                continue
            key = (point.evidence_type, f"{point.latitude:.6f}", f"{point.longitude:.6f}")
            if key in seen:
                continue
            seen.add(key)
            points.append(point)
            if len(points) >= limit:
                return points

    return points
