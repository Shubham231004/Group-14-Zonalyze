from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional, Tuple

from app.core.config import MAPBOX_ACCESS_TOKEN


MAPBOX_REVERSE_GEOCODE_URL = "https://api.mapbox.com/search/geocode/v6/reverse"
MAPBOX_TIMEOUT_SECONDS = 6

# This is intentionally an in-memory cache only. Mapbox temporary geocoding
# results should not be persisted unless the project is using Mapbox permanent
# geocoding terms. The cache only prevents duplicate calls during one backend run.
_ADDRESS_CACHE: Dict[Tuple[float, float], Optional[str]] = {}
_LAST_REQUEST_AT = 0.0


def _safe_float(value: object) -> Optional[float]:
    try:
        number = float(value)  # type: ignore[arg-type]
        if math.isfinite(number):
            return number
    except Exception:
        return None
    return None


def _cache_key(latitude: float, longitude: float) -> Tuple[float, float]:
    return (round(latitude, 6), round(longitude, 6))


def _pick_address_from_mapbox_response(payload: Dict) -> Optional[str]:
    features = payload.get("features") or []
    if not isinstance(features, list) or not features:
        return None

    first = features[0] or {}
    properties = first.get("properties") or {}

    # Mapbox v6 usually provides full_address for address-level reverse geocoding.
    for key in ("full_address", "place_formatted"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    name = properties.get("name")
    place_formatted = properties.get("place_formatted")
    if isinstance(name, str) and name.strip() and isinstance(place_formatted, str) and place_formatted.strip():
        return f"{name.strip()}, {place_formatted.strip()}"

    if isinstance(name, str) and name.strip():
        return name.strip()

    return None


def reverse_geocode_address(latitude: float, longitude: float) -> Optional[str]:
    """Return a display address for coordinates using Mapbox reverse geocoding.

    This function is optional and safe. If MAPBOX_ACCESS_TOKEN is missing or the
    request fails, it returns None and the rest of the map continues to work.
    """
    global _LAST_REQUEST_AT

    if not MAPBOX_ACCESS_TOKEN:
        return None

    lat = _safe_float(latitude)
    lon = _safe_float(longitude)
    if lat is None or lon is None:
        return None

    key = _cache_key(lat, lon)
    if key in _ADDRESS_CACHE:
        return _ADDRESS_CACHE[key]

    # Small throttle so a scenario with many missing addresses does not fire all
    # requests at the exact same millisecond.
    elapsed = time.time() - _LAST_REQUEST_AT
    if elapsed < 0.08:
        time.sleep(0.08 - elapsed)

    params = {
        "longitude": f"{lon:.7f}",
        "latitude": f"{lat:.7f}",
        "types": "address",
        "language": "en",
        "country": "ca",
        "limit": "1",
        "access_token": MAPBOX_ACCESS_TOKEN,
    }
    url = f"{MAPBOX_REVERSE_GEOCODE_URL}?{urllib.parse.urlencode(params)}"

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ZonalyzeCapstone/1.0 (educational prototype)",
                "Accept": "application/json",
            },
            method="GET",
        )
        _LAST_REQUEST_AT = time.time()
        with urllib.request.urlopen(request, timeout=MAPBOX_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        address = _pick_address_from_mapbox_response(payload)
    except Exception:
        address = None

    _ADDRESS_CACHE[key] = address
    return address


def enrich_missing_addresses(elements: Iterable[Dict], max_requests: int = 20) -> List[Dict]:
    """Fill missing competitor addresses without changing marker selection.

    The input POI list is copied. Existing OpenStreetMap addresses are preserved.
    Mapbox is used only for POIs with missing addresses and only up to max_requests.
    """
    enriched: List[Dict] = []
    requests_used = 0

    for element in elements:
        item = dict(element)

        if item.get("address"):
            item.setdefault("address_source", "openstreetmap_tags")
            enriched.append(item)
            continue

        if requests_used < max_requests:
            lat = _safe_float(item.get("latitude"))
            lon = _safe_float(item.get("longitude"))
            if lat is not None and lon is not None:
                address = reverse_geocode_address(lat, lon)
                requests_used += 1
                if address:
                    item["address"] = address
                    item["address_source"] = "mapbox_reverse_geocode"

        enriched.append(item)

    return enriched
