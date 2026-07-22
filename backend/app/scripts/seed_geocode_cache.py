"""One-time seeding of municipality centre coordinates.

Every municipality in the census dataset is geocoded once via OpenStreetMap
Nominatim and written to ``app/data/generated/municipality_geocode_cache.json``,
so that at runtime a city switch resolves instantly from the cache instead of a
live (rate-limited) geocode call. This is what makes the dropdown reliable.

Run once (respects Nominatim's ~1 request/second usage policy), then commit the
updated cache file:

    cd backend
    python -m app.scripts.seed_geocode_cache
"""

from __future__ import annotations

import time
from typing import List

from app.services.catalog_service import get_municipalities
from app.services.geospatial_service import (
    MUNICIPALITY_CENTERS,
    _geocode_municipality_with_osm,
    _load_geocode_cache,
    _normalize_place_name,
)


def seed(sleep_seconds: float = 1.1) -> None:
    municipalities = get_municipalities()
    total = len(municipalities)
    print(f"Seeding geocode cache for {total} municipalities from the census dataset...")

    seeded = 0
    skipped_hardcoded = 0
    already_cached = 0
    failed: List[str] = []

    for index, row in enumerate(municipalities, start=1):
        name = _normalize_place_name(str(row.get("municipality_name") or ""))
        if not name:
            continue
        if name in MUNICIPALITY_CENTERS:
            skipped_hardcoded += 1
            continue
        if name.lower() in _load_geocode_cache():
            already_cached += 1
            continue

        coord = _geocode_municipality_with_osm(name)  # writes to cache on success
        if coord:
            seeded += 1
            print(f"  [{index}/{total}] {name} -> {round(coord[0], 4)}, {round(coord[1], 4)}")
        else:
            failed.append(name)
            print(f"  [{index}/{total}] {name} -> FAILED to geocode")
        time.sleep(sleep_seconds)  # be polite to the public Nominatim endpoint

    print("\nDone.")
    print(f"  hardcoded (instant, skipped): {skipped_hardcoded}")
    print(f"  already cached:               {already_cached}")
    print(f"  newly seeded:                 {seeded}")
    print(f"  failed:                       {len(failed)}")
    if failed:
        print("  failed municipalities:", ", ".join(failed[:25]))
        print("  Re-run later to retry failures (Nominatim may have rate-limited this run).")


if __name__ == "__main__":
    seed()
