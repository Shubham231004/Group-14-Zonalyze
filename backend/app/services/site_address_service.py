from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.schemas.site_address import (
    SiteAddressAnalysisRequest,
    SiteAddressAnalysisResponse,
    SiteCoordinate,
    SiteEvidenceItem,
    SiteEvidenceSummary,
    SiteGeocodeCandidate,
)
from app.services.osm_service import (
    fetch_osm_commercial_activity,
    fetch_osm_competitors,
    fetch_osm_transit,
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).lower()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _confidence_from_geocode(row: Dict[str, Any]) -> str:
    importance = row.get("importance")
    try:
        score = float(importance)
    except Exception:
        score = 0.0
    if score >= 0.55:
        return "high"
    if score >= 0.30:
        return "moderate"
    return "limited"


def _extract_resolved_municipality(row: Dict[str, Any]) -> Optional[str]:
    address = row.get("address") if isinstance(row.get("address"), dict) else {}
    candidates = [
        address.get("city"),
        address.get("town"),
        address.get("municipality"),
        address.get("village"),
        address.get("county"),
    ]
    for value in candidates:
        text = _normalize_text(value)
        if text:
            return text
    display_name = _normalize_text(row.get("display_name"))
    if display_name:
        return display_name.split(",")[0].strip() or None
    return None


def _municipality_matches(requested: str, resolved: Optional[str], display_name: str) -> bool:
    requested_key = _normalize_key(requested)
    resolved_key = _normalize_key(resolved)
    display_key = _normalize_key(display_name)
    if not requested_key:
        return False
    if resolved_key and requested_key == resolved_key:
        return True
    # Nominatim sometimes puts the municipality only in the display name.
    return requested_key in display_key


def _nominatim_row_to_candidate(row: Dict[str, Any], requested_municipality: str) -> Optional[SiteGeocodeCandidate]:
    try:
        lat = float(row["lat"])
        lon = float(row["lon"])
    except Exception:
        return None
    display_name = str(row.get("display_name") or "OpenStreetMap geocode candidate")
    resolved_municipality = _extract_resolved_municipality(row)
    importance = None
    try:
        if row.get("importance") is not None:
            importance = float(row.get("importance"))
    except Exception:
        importance = None
    return SiteGeocodeCandidate(
        display_name=display_name,
        latitude=round(lat, 6),
        longitude=round(lon, 6),
        resolved_municipality=resolved_municipality,
        municipality_match=_municipality_matches(requested_municipality, resolved_municipality, display_name),
        confidence=_confidence_from_geocode(row),
        importance=importance,
    )


# Nominatim allows ~1 request/second and throttles callers that ignore it. The
# map re-geocodes the active address on every refresh (i.e. every radius change),
# so without this the same address burned 3 requests per drag and got rate-limited
# into "could not be geocoded". Successes only — caching a throttled failure would
# make it permanent for that address.
_GEOCODE_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _geocode_cache_key(address_line: str, municipality_name: str) -> Tuple[str, str]:
    return (_normalize_key(address_line), _normalize_key(municipality_name))


def _geocode_site_address(address_line: str, municipality_name: str) -> Tuple[Optional[Dict[str, Any]], List[SiteGeocodeCandidate], List[str]]:
    warnings: List[str] = []
    all_rows: List[Dict[str, Any]] = []
    seen = set()

    cached = _GEOCODE_CACHE.get(_geocode_cache_key(address_line, municipality_name))
    if cached is not None:
        return dict(cached), [], []

    query_variants = [
        f"{address_line}, {municipality_name}, Ontario, Canada",
        f"{address_line}, {municipality_name}, ON, Canada",
        f"{address_line}, Ontario, Canada",
    ]
    headers = {
        "User-Agent": "ZonalyzeCapstone/1.0 site-address-analysis",
        "Accept": "application/json",
    }

    for query in query_variants:
        try:
            response = requests.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": 5,
                    "countrycodes": "ca",
                    "addressdetails": 1,
                },
                headers=headers,
                timeout=8,
            )
            response.raise_for_status()
            rows = response.json() or []
            for row in rows:
                key = str(row.get("place_id") or row.get("osm_id") or row.get("display_name") or "")
                if key and key not in seen:
                    seen.add(key)
                    all_rows.append(row)
        except Exception as exc:
            warnings.append(f"Geocoding attempt failed for '{query}': {type(exc).__name__}")

        if all_rows:
            break  # first variant that resolves wins; don't spend the rate limit re-asking

    candidates: List[SiteGeocodeCandidate] = []
    for row in all_rows[:8]:
        candidate = _nominatim_row_to_candidate(row, municipality_name)
        if candidate:
            candidates.append(candidate)

    if not all_rows:
        return None, candidates, warnings

    # Prefer a result that matches the requested municipality. If none match,
    # keep the top result but mark the final analysis as needs_review later.
    selected = None
    for row in all_rows:
        candidate = _nominatim_row_to_candidate(row, municipality_name)
        if candidate and candidate.municipality_match:
            selected = row
            break
    if selected is None:
        selected = all_rows[0]

    resolved = {
        "latitude": float(selected["lat"]),
        "longitude": float(selected["lon"]),
        "display_name": str(selected.get("display_name") or address_line),
        "importance": selected.get("importance"),
        "type": selected.get("type"),
        "class": selected.get("class"),
        "resolved_municipality": _extract_resolved_municipality(selected),
        "address": selected.get("address") if isinstance(selected.get("address"), dict) else {},
    }
    _GEOCODE_CACHE[_geocode_cache_key(address_line, municipality_name)] = resolved
    return dict(resolved), candidates, warnings


def _poi_to_evidence_item(poi: Dict[str, Any], center_lat: float, center_lon: float) -> Optional[SiteEvidenceItem]:
    try:
        lat = float(poi["latitude"])
        lon = float(poi["longitude"])
    except Exception:
        return None
    name = str(poi.get("name") or poi.get("category") or "OpenStreetMap evidence point")
    category = str(poi.get("category") or "OpenStreetMap evidence")
    distance = poi.get("distance_km")
    try:
        distance_km = float(distance)
    except Exception:
        distance_km = _haversine_km(center_lat, center_lon, lat, lon)
    return SiteEvidenceItem(
        name=name,
        category=category,
        distance_km=round(distance_km, 3),
        latitude=round(lat, 6),
        longitude=round(lon, 6),
        address=poi.get("address"),
    )


def _summary_from_pois(
    pois: List[Dict[str, Any]],
    center_lat: float,
    center_lon: float,
    *,
    source_status: str,
    source_note: str,
    skipped_note: Optional[str] = None,
    limit: int = 8,
) -> SiteEvidenceSummary:
    if skipped_note:
        return SiteEvidenceSummary(count=0, items=[], status="skipped", note=skipped_note)

    if source_status != "live_osm":
        return SiteEvidenceSummary(
            count=0,
            items=[],
            status="query_failed",
            note=(
                "Evidence query failed or timed out. This count should not be interpreted as zero nearby evidence points. "
                f"Details: {source_note}"
            ),
        )

    items: List[SiteEvidenceItem] = []
    for poi in pois:
        item = _poi_to_evidence_item(poi, center_lat, center_lon)
        if item:
            items.append(item)
    items.sort(key=lambda row: row.distance_km)
    visible = items[:limit]

    if not items:
        return SiteEvidenceSummary(
            count=0,
            nearest=None,
            items=[],
            status="no_results",
            note="The public OSM query completed, but no matching evidence points were found within the selected radius.",
        )

    return SiteEvidenceSummary(
        count=len(items),
        nearest=visible[0] if visible else None,
        items=visible,
        status="available",
        note=source_note,
    )


def analyze_site_address(request: SiteAddressAnalysisRequest) -> SiteAddressAnalysisResponse:
    geocode, geocode_candidates, geocode_warnings = _geocode_site_address(request.address_line, request.municipality_name)

    empty_summary = SiteEvidenceSummary(count=0, items=[], status="skipped", note="Evidence was not queried because the address was not confidently geocoded.")

    if not geocode:
        return SiteAddressAnalysisResponse(
            status="geocode_failed",
            input_address=request.address_line,
            resolved_address=None,
            resolved_municipality=None,
            municipality_name=request.municipality_name,
            municipality_match=False,
            radius_km=request.radius_km,
            coordinate=None,
            geocode_source="OpenStreetMap Nominatim",
            geocode_confidence="unavailable",
            geocode_candidates=geocode_candidates,
            competitor_evidence=empty_summary,
            transit_evidence=empty_summary,
            commercial_activity_evidence=empty_summary,
            source_method="site_address_geocoding_failed_no_synthetic_site_evidence",
            user_facing_note="Zonalyze could not geocode this address, so it did not create site-level evidence for it.",
            warnings=[*geocode_warnings, "Try adding street number, city, province, or postal code."],
            next_steps=["Confirm the address spelling.", "Try a nearby landmark or full postal address."],
        )

    lat = float(geocode["latitude"])
    lon = float(geocode["longitude"])
    resolved_address = str(geocode.get("display_name") or request.address_line)
    resolved_municipality = _normalize_text(geocode.get("resolved_municipality")) or None
    municipality_match = _municipality_matches(request.municipality_name, resolved_municipality, resolved_address)
    geocode_confidence = _confidence_from_geocode(geocode)

    warnings: List[str] = list(geocode_warnings)
    if not municipality_match:
        warnings.append(
            f"The resolved address appears to be in '{resolved_municipality or 'an unknown municipality'}', "
            f"but the requested municipality is '{request.municipality_name}'. Confirm the address before using this site analysis."
        )
    if geocode_confidence == "limited":
        warnings.append("The address match has limited geocode confidence. Confirm the resolved address before trusting site-level evidence.")

    transit = fetch_osm_transit(center_lat=lat, center_lon=lon, radius_km=request.radius_km, limit=40)
    commercial = fetch_osm_commercial_activity(center_lat=lat, center_lon=lon, radius_km=request.radius_km, limit=40)

    competitor_result = None
    competitor_skipped_note: Optional[str] = None
    if request.business_subcategory:
        competitor_result = fetch_osm_competitors(
            business_subcategory=request.business_subcategory,
            center_lat=lat,
            center_lon=lon,
            radius_km=request.radius_km,
            limit=50,
        )
    else:
        competitor_skipped_note = "No catalog business_subcategory was supplied, so site-level competitor lookup was skipped."
        warnings.append(competitor_skipped_note)

    competitor_summary = _summary_from_pois(
        competitor_result.elements if competitor_result else [],
        lat,
        lon,
        source_status=competitor_result.status if competitor_result else "skipped",
        source_note=competitor_result.note if competitor_result else competitor_skipped_note or "Competitor lookup skipped.",
        skipped_note=competitor_skipped_note,
    )
    transit_summary = _summary_from_pois(
        transit.elements,
        lat,
        lon,
        source_status=transit.status,
        source_note=transit.note,
    )
    commercial_summary = _summary_from_pois(
        commercial.elements,
        lat,
        lon,
        source_status=commercial.status,
        source_note=commercial.note,
    )

    for summary_name, summary in [
        ("Competitor", competitor_summary),
        ("Transit", transit_summary),
        ("Commercial activity", commercial_summary),
    ]:
        if summary.status == "query_failed" and summary.note:
            warnings.append(f"{summary_name} evidence unavailable: {summary.note}")

    status = "available"
    if not municipality_match or geocode_confidence == "limited":
        status = "needs_review"

    if status == "needs_review":
        note = (
            "Zonalyze found a possible address match, but the geocode needs review before this site-level evidence should be trusted. "
            "Confirm the resolved address and municipality first."
        )
    else:
        note = (
            "This is site-level public map evidence from OpenStreetMap/Nominatim/Overpass. "
            "It supports address-level screening, but it is not a verified lease listing or live pedestrian count."
        )

    return SiteAddressAnalysisResponse(
        status=status,
        input_address=request.address_line,
        resolved_address=resolved_address,
        resolved_municipality=resolved_municipality,
        municipality_name=request.municipality_name,
        municipality_match=municipality_match,
        radius_km=request.radius_km,
        coordinate=SiteCoordinate(latitude=round(lat, 6), longitude=round(lon, 6)),
        geocode_source="OpenStreetMap Nominatim",
        geocode_confidence=geocode_confidence,
        geocode_candidates=geocode_candidates[:5],
        competitor_evidence=competitor_summary,
        transit_evidence=transit_summary,
        commercial_activity_evidence=commercial_summary,
        source_method="site_address_osm_nominatim_plus_overpass_evidence_with_geocode_validation_guard",
        user_facing_note=note,
        warnings=warnings[:10],
        next_steps=[
            "Confirm the resolved address and municipality before using this site evidence.",
            "Use this site evidence to compare addresses before deeper lease or inspection research.",
            "Verify the exact property, storefront access, parking, and lease terms before making an investment decision.",
        ],
    )
