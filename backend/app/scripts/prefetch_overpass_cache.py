"""Prefetch Overpass competitor/transit/commercial data into the disk cache.

Public Overpass is often blocked or throttled (campus networks especially), which
blanks the market map. Run this ONCE on a working network (e.g. a phone hotspot)
to populate app/data/generated/overpass_cache.json for your demo cities and
businesses. After that the map loads instantly from the cache and keeps showing
competitors even when Overpass is unreachable — commit the cache file so it ships.

    cd backend
    python -m app.scripts.prefetch_overpass_cache

Env knobs:
    PREFETCH_RADIUS_KM (default 5)   PREFETCH_SLEEP (default 0.4s between calls)
"""

from __future__ import annotations

import os
import time
from typing import List

from app.catalogs.business_subcategories import list_business_subcategory_options
from app.services.geospatial_service import (
    MUNICIPALITY_CENTERS,
    _center_for_municipality,
    _load_geocode_cache,
)
from app.services.osm_service import (
    fetch_osm_commercial_activity,
    fetch_osm_competitors,
    fetch_osm_transit,
)

_ONTARIO_FALLBACK = (44.0000, -79.5000)


def _demo_cities() -> List[str]:
    # Cities that already resolve to a centre without a fresh live geocode: the
    # hardcoded Waterloo-region set plus anything already in the geocode cache.
    cities = list(MUNICIPALITY_CENTERS.keys())
    for cached_name in _load_geocode_cache().keys():
        title = cached_name.title()
        if title not in cities:
            cities.append(title)
    return cities


def prefetch(radius_km: float, sleep_seconds: float) -> None:
    cities = _demo_cities()
    businesses = [opt["business_subcategory"] for opt in list_business_subcategory_options()]
    print(
        f"Prefetching Overpass cache for {len(cities)} cities x {len(businesses)} businesses "
        f"at {radius_km} km (plus transit + commercial per city)..."
    )

    ok = 0
    empty = 0
    for city_index, city in enumerate(cities, start=1):
        lat, lon = _center_for_municipality(city)
        if (round(lat, 4), round(lon, 4)) == _ONTARIO_FALLBACK:
            print(f"[{city_index}/{len(cities)}] {city}: no centre resolved, skipping.")
            continue
        print(f"[{city_index}/{len(cities)}] {city} ({round(lat,3)}, {round(lon,3)})")

        # Transit + commercial are business-independent — fetch once per city.
        for label, fn in (("transit", fetch_osm_transit), ("commercial", fetch_osm_commercial_activity)):
            res = fn(center_lat=lat, center_lon=lon, radius_km=radius_km)
            print(f"    {label:10} -> {res.status} ({len(res.elements)})")
            time.sleep(sleep_seconds)

        for business in businesses:
            res = fetch_osm_competitors(
                business_subcategory=business,
                center_lat=lat,
                center_lon=lon,
                radius_km=radius_km,
                limit=60,
            )
            if res.status == "live_osm":
                ok += 1
                if not res.elements:
                    empty += 1
            print(f"    {business[:34]:34} -> {res.status} ({len(res.elements)})")
            time.sleep(sleep_seconds)

    print("\nDone.")
    print(f"  live competitor fetches: {ok}  (of which {empty} legitimately had 0 nearby)")
    print("  Cache written to app/data/generated/overpass_cache.json — commit it so the demo ships with data.")


if __name__ == "__main__":
    prefetch(
        radius_km=float(os.getenv("PREFETCH_RADIUS_KM", "5")),
        sleep_seconds=float(os.getenv("PREFETCH_SLEEP", "0.4")),
    )
