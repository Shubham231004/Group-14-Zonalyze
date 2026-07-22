from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import requests

from app.ml.scenario_feature_builder import build_prediction_features
from app.schemas.geospatial import (
    BusinessResolutionMapContext,
    DynamicOSMTagContext,
    GeoCoordinate,
    GeospatialMarketContext,
    GeospatialMarketRequest,
    HeatmapCell,
    MapMarker,
)
from app.schemas.scenario import AnalyzeScenarioRequest
from app.services.competition_data_service import (
    build_osm_competition_evidence,
    get_competition_observation,
)
from app.services.demand_data_service import get_demand_evidence
from app.services.lease_cost_data_service import get_lease_cost_evidence
from app.services.osm_service import (
    OSMFetchResult,
    fetch_osm_competitors,
    fetch_osm_pois_by_resolved_tags,
    fetch_osm_transit,
    fetch_osm_commercial_activity,
)
from app.services.mapbox_geocoding_service import enrich_missing_addresses
from app.schemas.business_resolver import BusinessResolveRequest
from app.services.business_resolver_service import resolve_business_query
from app.services.business_matching_service import map_idea_to_catalog_subcategory
from app.services.site_address_service import _geocode_site_address, _confidence_from_geocode
from app.services.footfall_heatmap_service import build_footfall_heatmap_points


APP_DIR = Path(__file__).resolve().parents[1]
GEOCODE_CACHE_PATH = APP_DIR / "data" / "generated" / "municipality_geocode_cache.json"

# Small offline seed for the main Waterloo Region municipalities only.
# For every other Ontario municipality, the service geocodes dynamically through OpenStreetMap Nominatim and caches the result.
MUNICIPALITY_CENTERS: Dict[str, Tuple[float, float]] = {
    "Kitchener": (43.4516, -80.4925),
    "Waterloo": (43.4643, -80.5204),
    "Cambridge": (43.3616, -80.3144),
    "Woolwich": (43.5668, -80.4831),
    "Wilmot": (43.4000, -80.6500),
    "Wellesley": (43.5500, -80.7500),
    "North Dumfries": (43.2830, -80.3830),
}


def _normalize_place_name(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    if not GEOCODE_CACHE_PATH.exists():
        return {}
    try:
        raw = json.loads(GEOCODE_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    cache: Dict[str, Tuple[float, float]] = {}
    for key, value in raw.items():
        try:
            lat = float(value["latitude"])
            lng = float(value["longitude"])
            if math.isfinite(lat) and math.isfinite(lng):
                cache[key] = (lat, lng)
        except Exception:
            continue
    return cache


def _save_geocode_cache(cache: Dict[str, Tuple[float, float]]) -> None:
    GEOCODE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    serializable = {
        key: {"latitude": lat, "longitude": lng}
        for key, (lat, lng) in sorted(cache.items())
    }
    GEOCODE_CACHE_PATH.write_text(json.dumps(serializable, indent=2), encoding="utf-8")


def _geocode_municipality_with_osm(municipality_name: str) -> Optional[Tuple[float, float]]:
    """Free dynamic geocoding through OpenStreetMap Nominatim.

    This makes the map center dynamic for any selected Ontario municipality such as Kingston,
    London, Ottawa, Toronto, etc. Results are cached locally in app/data/generated.
    """
    name = _normalize_place_name(municipality_name)
    if not name:
        return None

    cache_key = name.lower()
    cache = _load_geocode_cache()
    if cache_key in cache:
        return cache[cache_key]

    query_variants = [
        f"{name}, Ontario, Canada",
        f"{name}, ON, Canada",
        f"City of {name}, Ontario, Canada",
        f"Township of {name}, Ontario, Canada",
    ]

    headers = {
        "User-Agent": "ZonalyzeCapstone/1.0 (local capstone prototype)",
        "Accept": "application/json",
    }

    for query in query_variants:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "ca",
                    "addressdetails": 1,
                },
                headers=headers,
                timeout=8,
            )
            response.raise_for_status()
            results = response.json()
            if not results:
                continue

            first = results[0]
            lat = float(first["lat"])
            lng = float(first["lon"])
            if math.isfinite(lat) and math.isfinite(lng):
                cache[cache_key] = (lat, lng)
                _save_geocode_cache(cache)
                return lat, lng
        except Exception:
            continue

    return None


def _center_for_municipality(municipality_name: str) -> Tuple[float, float]:
    name = _normalize_place_name(municipality_name)

    if name in MUNICIPALITY_CENTERS:
        return MUNICIPALITY_CENTERS[name]

    dynamic_center = _geocode_municipality_with_osm(name)
    if dynamic_center:
        return dynamic_center

    # Do not silently fall back to Kitchener for unknown municipalities.
    # This fallback is only to keep the API alive when offline/geocoding fails.
    # The returned evidence note below makes the limitation visible.
    return (44.0000, -79.5000)


def _offset_coordinate(lat: float, lng: float, x_pct: float, y_pct: float, radius_km: float) -> Tuple[float, float]:
    km_x = (x_pct / 100.0) * radius_km
    km_y = (y_pct / 100.0) * radius_km
    lat_offset = km_y / 111.0
    lng_offset = km_x / (111.0 * max(math.cos(math.radians(lat)), 0.2))
    return lat + lat_offset, lng + lng_offset


def _xy_offsets_from_coordinate(center_lat: float, center_lng: float, lat: float, lng: float, radius_km: float) -> Tuple[float, float]:
    km_y = (lat - center_lat) * 111.0
    km_x = (lng - center_lng) * 111.0 * max(math.cos(math.radians(center_lat)), 0.2)
    if radius_km <= 0:
        return 0.0, 0.0
    return (km_x / radius_km) * 100.0, (km_y / radius_km) * 100.0


def _marker_offsets(count: int) -> List[Tuple[float, float]]:
    base = [
        (-38, -12), (-24, 28), (-10, -35), (12, 18), (26, -22),
        (38, 8), (-44, 36), (44, -38), (0, 42), (18, -46),
    ]
    return base[: max(0, min(count, len(base)))]


def _fallback_competitor_markers(
    center_lat: float,
    center_lng: float,
    radius_km: float,
    competitor_count: int,
    intensity: float,
    credibility: str,
    source_method: str,
) -> List[MapMarker]:
    rendered_competitors = min(max(competitor_count, 1), 10)
    markers: List[MapMarker] = []
    for index, (x_pct, y_pct) in enumerate(_marker_offsets(rendered_competitors), start=1):
        lat, lng = _offset_coordinate(center_lat, center_lng, x_pct, y_pct, radius_km)
        markers.append(
            MapMarker(
                marker_id=f"competitor-proxy-{index}",
                marker_type="competitor_proxy",
                label=f"Proxy competitor marker {index}",
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                x_offset_pct=x_pct,
                y_offset_pct=y_pct,
                intensity=float(intensity),
                source_method=source_method,
                credibility=credibility,
                category="Proxy competitor",
                tags={},
            )
        )
    return markers


def _build_heatmap_cells(
    center_lat: float,
    center_lng: float,
    radius_km: float,
    demand_index: float,
    risk_index: float,
) -> List[HeatmapCell]:
    cells: List[HeatmapCell] = []
    offsets = [(-35, 30), (0, 36), (35, 30), (-28, 0), (0, 0), (28, 0), (-35, -30), (0, -36), (35, -30)]
    for i, (x_pct, y_pct) in enumerate(offsets, start=1):
        lat, lng = _offset_coordinate(center_lat, center_lng, x_pct, y_pct, radius_km)
        center_bias = max(0.0, 1.0 - (abs(x_pct) + abs(y_pct)) / 100.0)
        demand = max(0, min(100, demand_index * (0.82 + center_bias * 0.28)))
        risk = max(0, min(100, risk_index * (0.78 + (1 - center_bias) * 0.35)))
        cells.append(
            HeatmapCell(
                cell_id=f"heat-{i}",
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                demand_intensity=round(demand, 2),
                risk_intensity=round(risk, 2),
                label=f"Demand {demand:.0f} / Risk {risk:.0f}",
                source_method="derived from demand, competition, and lease evidence layers",
            )
        )
    return cells



def _get_request_value(request: Any, field_name: str, default: Any = None) -> Any:
    return getattr(request, field_name, default)


def _business_resolution_to_map_context(resolution) -> BusinessResolutionMapContext:
    return BusinessResolutionMapContext(
        status=resolution.status,
        input_text=resolution.input_text,
        normalized_business_name=resolution.normalized_business_name,
        primary_category=resolution.primary_category,
        secondary_categories=resolution.secondary_categories,
        brand_terms=resolution.brand_terms,
        specialty_terms=resolution.specialty_terms,
        osm_tags=[
            DynamicOSMTagContext(
                key=tag.key,
                value=tag.value,
                confidence=tag.confidence,
                tag_role=tag.tag_role,
                reason=tag.reason,
            )
            for tag in resolution.osm_tags
        ],
        resolution_confidence=resolution.resolution_confidence,
        confidence_score=resolution.confidence_score,
        source_method=resolution.source_method,
        raw_ai_available=resolution.raw_ai_available,
        warnings=resolution.warnings,
        raw_ai_error=resolution.raw_ai_error,
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
        if not math.isfinite(number):
            return default
        return number
    except Exception:
        return default


def build_geospatial_market_context(request: GeospatialMarketRequest | AnalyzeScenarioRequest) -> GeospatialMarketContext:
    """Build market-map evidence with optional dynamic business-query OSM tags.

    Backward compatibility:
    - Existing calls with business_subcategory continue to use the old catalog/evidence path.

    Step 27B dynamic path:
    - If business_query is supplied, the service resolves it through the dynamic business
      resolver and uses the validated AI-generated OSM tags for competitor/POI markers.
    - No hardcoded business-to-OSM mapping is added here.
    - If resolution fails, the map stays alive but returns no invented competitor markers.
    """
    municipality_name = _normalize_place_name(_get_request_value(request, "municipality_name", ""))
    radius_km = float(_get_request_value(request, "radius_km", 5) or 5)
    business_subcategory_raw = _get_request_value(request, "business_subcategory", None)
    business_query_raw = _get_request_value(request, "business_query", None)
    model = _get_request_value(request, "model", None)

    business_subcategory = _normalize_place_name(business_subcategory_raw or "")
    business_query = _normalize_place_name(business_query_raw or "")

    business_resolution_context: Optional[BusinessResolutionMapContext] = None
    resolved_business_name: Optional[str] = None
    dynamic_resolution = None

    if business_query:
        dynamic_resolution = resolve_business_query(
            BusinessResolveRequest(
                business_query=business_query,
                municipality_name=municipality_name,
                model=model,
            )
        )
        business_resolution_context = _business_resolution_to_map_context(dynamic_resolution)
        if dynamic_resolution.status == "resolved":
            resolved_business_name = dynamic_resolution.normalized_business_name or business_query

    display_business_name = resolved_business_name or business_subcategory or business_query or "Unresolved business idea"

    # --- Location anchor: a specific address (precise) if given, else city centre ---
    # The user's input decides the reference point. When a real address geocodes,
    # the radius and every OSM evidence layer centre on that exact point, and the
    # census/ML uses the municipality the address actually falls in.
    site_address = _normalize_place_name(_get_request_value(request, "site_address", "") or "")
    anchor_type = "city_center"
    resolved_address: Optional[str] = None
    geocode_confidence: Optional[str] = None
    municipality_match: Optional[bool] = None
    anchor_note = ""
    census_municipality = municipality_name

    if site_address:
        geocode, _candidates, _warnings = _geocode_site_address(site_address, municipality_name)
        if geocode:
            center_lat = float(geocode["latitude"])
            center_lng = float(geocode["longitude"])
            anchor_type = "address"
            resolved_address = str(geocode.get("display_name") or site_address)
            geocode_confidence = _confidence_from_geocode(geocode)
            resolved_muni = _normalize_place_name(str(geocode.get("resolved_municipality") or ""))
            municipality_match = bool(resolved_muni) and resolved_muni.lower() == municipality_name.lower()
            census_municipality = resolved_muni or municipality_name
            anchor_note = f"Analysis centred on the geocoded address: {resolved_address}."
        else:
            center_lat, center_lng = _center_for_municipality(municipality_name)
            anchor_note = (
                f"The address '{site_address}' could not be geocoded, so the analysis is centred on "
                f"{municipality_name} city centre instead. Add a full street address for site-level accuracy."
            )
    else:
        center_lat, center_lng = _center_for_municipality(municipality_name)
        anchor_note = (
            f"Centred on {municipality_name} city centre. Add a specific address for site-level accuracy."
        )

    geocode_fallback_used = (round(center_lat, 4), round(center_lng, 4)) == (44.0000, -79.5000)

    # --- Feasibility scoring basis: exact catalog, nearest catalog, or unavailable ---
    # The ML model only knows the trained catalog subcategories. A free-text idea is
    # mapped to the closest trained type so a score can still be shown -- clearly
    # labelled as an approximation -- or honestly reported as unavailable.
    if business_subcategory:
        score_subcategory: Optional[str] = business_subcategory
        score_basis = "exact_catalog"
        score_basis_note = f"Feasibility uses the trained model for '{business_subcategory}'."
    elif dynamic_resolution is not None:
        match = map_idea_to_catalog_subcategory(dynamic_resolution, raw_text=business_query)
        score_subcategory = match.subcategory
        score_basis = match.basis
        score_basis_note = match.label
    else:
        score_subcategory = None
        score_basis = "unavailable"
        score_basis_note = "No trained business type was provided, so no feasibility score is available."

    analysis_business_subcategory = score_subcategory or business_subcategory or display_business_name

    features: Dict[str, Any] = {}
    competition = None
    demand = None
    lease = None

    if score_subcategory:
        try:
            features = build_prediction_features(
                municipality_name=census_municipality,
                business_subcategory=score_subcategory,
                radius_km=radius_km,
            )
            population = float(features.get("population_2021", 0) or 0)
            competition = get_competition_observation(
                municipality_name=census_municipality,
                business_subcategory=score_subcategory,
                radius_km=radius_km,
                population=population,
            )
            demand = get_demand_evidence(
                municipality_name=census_municipality,
                business_subcategory=score_subcategory,
                radius_km=radius_km,
                features=features,
            )
            lease = get_lease_cost_evidence(
                municipality_name=census_municipality,
                business_subcategory=score_subcategory,
                radius_km=radius_km,
                features=features,
            )
        except Exception:
            # Census/model data may not exist for this municipality or type. We do
            # not fake financial/demand/lease evidence; the map still shows OSM POIs.
            features = {}
            competition = None
            demand = None
            lease = None

    def _fetch_competitors() -> OSMFetchResult:
        if dynamic_resolution is not None:
            if dynamic_resolution.status == "resolved" and dynamic_resolution.osm_tags:
                return fetch_osm_pois_by_resolved_tags(
                    resolved_tags=dynamic_resolution.osm_tags,
                    business_label=display_business_name,
                    center_lat=center_lat,
                    center_lon=center_lng,
                    radius_km=radius_km,
                    limit=60,
                )
            return OSMFetchResult(
                status="business_resolution_needs_review",
                note=(
                    "Dynamic business resolution did not produce validated OSM tags. "
                    "Zonalyze did not query or invent competitor markers for this business idea."
                ),
                elements=[],
            )
        return fetch_osm_competitors(
            business_subcategory=analysis_business_subcategory,
            center_lat=center_lat,
            center_lon=center_lng,
            radius_km=radius_km,
            limit=60,
        )

    # The three OSM queries are independent network calls. Running them in parallel
    # bounds the market-map latency to the slowest single query instead of the sum
    # of all three — the difference between a map that renders and one that trips
    # the frontend's request timeout when a mirror is slow. (Overpass mirror
    # failover already lives in osm_service._fetch_overpass.)
    with ThreadPoolExecutor(max_workers=3) as pool:
        competitor_future = pool.submit(_fetch_competitors)
        transit_future = pool.submit(
            fetch_osm_transit,
            center_lat=center_lat,
            center_lon=center_lng,
            radius_km=radius_km,
            limit=30,
        )
        commercial_future = pool.submit(
            fetch_osm_commercial_activity,
            center_lat=center_lat,
            center_lon=center_lng,
            radius_km=radius_km,
            limit=50,
        )
        competitor_result = competitor_future.result()
        transit_result = transit_future.result()
        commercial_activity_result = commercial_future.result()

    competitor_pois = enrich_missing_addresses(
        competitor_result.elements,
        max_requests=20,
    )

    # Real-data competition: build sourced evidence from the OSM competitors the
    # map already fetched (zero extra latency). Prefer this over the catalog seed /
    # formula proxy. This is display/decision evidence only — the ML feature vector
    # is untouched. Falls back to the seed observation when OSM is not live.
    osm_population = _safe_float(features.get("population_2021"), 0.0)
    osm_competition_evidence = build_osm_competition_evidence(
        municipality_name=municipality_name,
        business_subcategory=display_business_name,
        population=osm_population,
        osm_elements=competitor_pois,
        is_live=(competitor_result.status == "live_osm"),
    )
    if osm_competition_evidence is not None:
        authoritative_competition = osm_competition_evidence
        competition_evidence_source = "openstreetmap_live"
    else:
        authoritative_competition = competition
        seed_method = str(getattr(competition, "method", "") or "")
        competition_evidence_source = (
            "catalog_seed" if seed_method.startswith("data_catalog") else "proxy"
        )

    markers: List[MapMarker] = []

    for index, poi in enumerate(competitor_pois[:35], start=1):
        x_pct, y_pct = _xy_offsets_from_coordinate(center_lat, center_lng, poi["latitude"], poi["longitude"], radius_km)
        markers.append(
            MapMarker(
                marker_id=f"osm-competitor-{index}-{poi.get('osm_id')}",
                marker_type="competitor",
                label=poi.get("name") or f"Market evidence POI {index}",
                latitude=round(float(poi["latitude"]), 6),
                longitude=round(float(poi["longitude"]), 6),
                x_offset_pct=round(x_pct, 2),
                y_offset_pct=round(y_pct, 2),
                intensity=float(_safe_float(getattr(authoritative_competition, "competition_pressure_index", None), 50.0)),
                source_method="OpenStreetMap Overpass API using dynamic AI-resolved tags" if dynamic_resolution else "OpenStreetMap Overpass API",
                credibility="medium" if competitor_result.status == "live_osm" else "limited",
                osm_id=poi.get("osm_id"),
                osm_type=poi.get("osm_type"),
                category=poi.get("category"),
                address=poi.get("address"),
                address_source=poi.get("address_source"),
                tags=poi.get("tags") or {},
            )
        )

    # Trust rule: never create proxy/fake competitor markers.
    # If Overpass fails or returns no relevant real POIs, the map should show no
    # competitor markers and explain the evidence gap in osm_query_note/evidence_note.

    demand_transit_intensity = _safe_float(getattr(demand, "transit_access_proxy_index", None), 50.0)
    for index, poi in enumerate(transit_result.elements[:18], start=1):
        x_pct, y_pct = _xy_offsets_from_coordinate(center_lat, center_lng, poi["latitude"], poi["longitude"], radius_km)
        markers.append(
            MapMarker(
                marker_id=f"osm-transit-{index}-{poi.get('osm_id')}",
                marker_type="transit",
                label=poi.get("name") or "Transit access point",
                latitude=round(float(poi["latitude"]), 6),
                longitude=round(float(poi["longitude"]), 6),
                x_offset_pct=round(x_pct, 2),
                y_offset_pct=round(y_pct, 2),
                intensity=demand_transit_intensity,
                source_method="OpenStreetMap Overpass API",
                credibility="medium" if transit_result.status == "live_osm" else "limited",
                osm_id=poi.get("osm_id"),
                osm_type=poi.get("osm_type"),
                category="Transit / mobility",
                address=poi.get("address"),
                address_source=poi.get("address_source"),
                tags=poi.get("tags") or {},
            )
        )

    footfall_heatmap_points = build_footfall_heatmap_points(
        competitor_pois=competitor_pois,
        transit_pois=transit_result.elements,
        commercial_activity_pois=commercial_activity_result.elements,
        limit=180,
    )
    if footfall_heatmap_points:
        footfall_heatmap_status = "available"
        footfall_heatmap_note = (
            "Footfall evidence heatmap is based on real public OpenStreetMap evidence points: "
            "business/competitor POIs, transit access points, and commercial activity POIs. "
            "It is a footfall-potential evidence layer, not live pedestrian count data."
        )
    else:
        footfall_heatmap_status = "no_public_osm_evidence"
        footfall_heatmap_note = (
            "No public OSM activity points were available for a footfall evidence heatmap in this radius. "
            "Zonalyze did not synthesize heatmap points."
        )

    competition_index = _safe_float(getattr(authoritative_competition, "competition_pressure_index", None), 0.0)
    demand_index = _safe_float(getattr(demand, "demand_pressure_index", None), 0.0)
    rent_index = _safe_float(getattr(lease, "rent_pressure_index", None), 0.0)

    heatmap_cells: List[HeatmapCell] = []
    if demand is not None and lease is not None:
        risk_index = min(100.0, max(0.0, (competition_index * 0.45) + (rent_index * 0.45) + ((100 - demand_index) * 0.10)))
        heatmap_cells = _build_heatmap_cells(
            center_lat=center_lat,
            center_lng=center_lng,
            radius_km=radius_km,
            demand_index=demand_index,
            risk_index=risk_index,
        )

    osm_statuses = {competitor_result.status, transit_result.status, commercial_activity_result.status}
    if "live_osm" in osm_statuses:
        osm_query_status = "live_osm_partial" if any(status != "live_osm" for status in osm_statuses) else "live_osm"
    elif "business_resolution_needs_review" in osm_statuses:
        osm_query_status = "business_resolution_needs_review"
    else:
        osm_query_status = "fallback_proxy"

    osm_query_note = " ".join(sorted({competitor_result.note, transit_result.note, commercial_activity_result.note}))

    evidence_note = (
        "OpenStreetMap points improve geospatial realism, but they do not guarantee complete market coverage. "
        "For free-text business ideas, competitor/POI markers come from validated OSM tags generated by the local AI business resolver. "
        "If the resolver cannot produce validated tags, Zonalyze does not invent competitor markers."
        if dynamic_resolution
        else "OpenStreetMap points improve geospatial realism, but they do not guarantee complete market coverage. The map currently displays direct competitor, transit-access, and footfall-potential evidence layers only when real public OSM evidence is available. Competitor addresses use OpenStreetMap address tags first, with optional Mapbox reverse-geocoding fallback when a Mapbox token is configured."
    )

    return GeospatialMarketContext(
        municipality_name=municipality_name,
        business_subcategory=display_business_name,
        business_query=business_query or None,
        resolved_business_name=resolved_business_name,
        business_resolution=business_resolution_context,
        radius_km=radius_km,
        center=GeoCoordinate(latitude=center_lat, longitude=center_lng),
        anchor_type=anchor_type,
        resolved_address=resolved_address,
        geocode_confidence=geocode_confidence,
        municipality_match=municipality_match,
        anchor_note=anchor_note,
        score_basis=score_basis,
        score_basis_subcategory=score_subcategory,
        score_basis_note=score_basis_note,
        map_method="mapbox_or_leaflet_osm_overpass_dynamic_business_tags" if dynamic_resolution else "mapbox_or_leaflet_osm_overpass_plus_evidence_layers",
        map_credibility="medium" if osm_query_status.startswith("live_osm") else "limited",
        coverage_note=(
            "The radius is dynamically centered on the selected municipality using cached coordinates or OpenStreetMap geocoding. Competitor and transit markers use live OpenStreetMap coordinates when available."
            if not geocode_fallback_used
            else "The selected municipality could not be geocoded online, so a temporary Ontario fallback center is shown. Check internet access or cache this municipality coordinate."
        ),
        evidence_note=evidence_note,
        radius_label=f"{radius_km:g} km analysis radius",
        competition_pressure_index=competition_index,
        demand_pressure_index=demand_index,
        rent_pressure_index=rent_index,
        marker_count=len(markers),
        real_competitor_count=len([m for m in markers if m.marker_type == "competitor"]),
        competition_evidence=authoritative_competition,
        competition_evidence_source=competition_evidence_source,
        transit_marker_count=len([m for m in markers if m.marker_type == "transit"]),
        lease_marker_count=0,
        markers=markers,
        heatmap_cells=heatmap_cells,
        footfall_heatmap_points=footfall_heatmap_points,
        footfall_heatmap_status=footfall_heatmap_status,
        footfall_heatmap_note=footfall_heatmap_note,
        footfall_heatmap_sources=[
            "OpenStreetMap business/competitor POIs",
            "OpenStreetMap transit/access POIs",
            "OpenStreetMap commercial activity POIs",
        ] if footfall_heatmap_points else [],
        osm_query_status=osm_query_status,
        osm_query_note=osm_query_note,
        next_data_needed=[
            "Overpass result-count coverage checks for resolved OSM tags",
            "Commercial lease listing coordinates and asking rents",
            "Observed pedestrian or mobility data for true foot-traffic intensity",
            "Municipal business licence data for more complete competitor coverage",
            "Neighbourhood or parcel boundaries for more precise site-level coverage",
        ],
    )
