"""Local PostGIS POI store — the owned, rate-limit-free source for competitor/POI
lookups. Replaces live public Overpass in the request path; Overpass stays only as
a fallback (see osm_service). Populated by app/scripts/import_pois.py.

Returns raw Overpass-shaped element dicts so the existing normalize + relevance
flow in osm_service is reused unchanged.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger("zonalyze.poi")

# Matches the radius clamp used for the Overpass query (250 m .. 25 km).
_MIN_RADIUS_M = 250
_MAX_RADIUS_M = 25000

# Same POI tag keys the app cares about (competitors/transit/commercial live under these).
POI_TAG_KEYS = ("shop", "amenity", "leisure", "office", "craft", "healthcare", "sport", "railway", "highway", "public_transport")

POI_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS poi (
    osm_type text NOT NULL,
    osm_id   bigint NOT NULL,
    name     text,
    category text,
    tags     jsonb NOT NULL DEFAULT '{}'::jsonb,
    lat      double precision NOT NULL,
    lon      double precision NOT NULL,
    geom     geography(Point, 4326)
             GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography) STORED,
    PRIMARY KEY (osm_type, osm_id)
);
CREATE INDEX IF NOT EXISTS poi_geom_gist ON poi USING gist (geom);
"""

# ponytail: cached once — flip to False->True needs a restart after the first import.
_poi_ready: Optional[bool] = None


def create_poi_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text(POI_SCHEMA_SQL))


def _build_tag_clause(tags: List[Tuple[str, str]]) -> Tuple[str, Dict[str, str]]:
    """(key,value) pairs -> a SQL OR clause + bound params. Keys/values both bound."""
    clauses, params = [], {}
    for i, (key, value) in enumerate(tags):
        clauses.append(f"tags ->> :k{i} = :v{i}")
        params[f"k{i}"] = str(key)
        params[f"v{i}"] = str(value)
    return (" OR ".join(clauses) or "FALSE"), params


def _row_to_element(row) -> Dict:
    """DB row -> Overpass-shaped element dict (osm_service._normalize_element input)."""
    tags = row.tags
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = {}
    return {"type": row.osm_type, "id": row.osm_id, "lat": row.lat, "lon": row.lon, "tags": tags or {}}


def _poi_available(conn) -> bool:
    global _poi_ready
    if _poi_ready is None:
        try:
            _poi_ready = bool(conn.execute(text("SELECT EXISTS (SELECT 1 FROM poi)")).scalar())
        except Exception:
            _poi_ready = False  # table missing / PostGIS absent -> caller falls back to Overpass
    return _poi_ready


def fetch_pois_from_db(
    tags: List[Tuple[str, str]],
    center_lat: float,
    center_lon: float,
    radius_km: float,
    limit: int,
) -> Optional[List[Dict]]:
    """Radius search over the local POI store.

    Returns raw element dicts (possibly empty = a real "none nearby" answer), or
    None when the store is unavailable/not imported yet so the caller falls back
    to Overpass.
    """
    if not tags or _poi_ready is False:  # store known-absent -> skip the DB round-trip
        return None
    radius_m = int(max(_MIN_RADIUS_M, min(radius_km * 1000, _MAX_RADIUS_M)))
    tag_clause, params = _build_tag_clause(tags)
    params.update({"lat": center_lat, "lon": center_lon, "radius_m": radius_m, "limit": int(max(limit, 1))})
    sql = text(
        f"""
        SELECT osm_type, osm_id, lat, lon, tags
        FROM poi
        WHERE ST_DWithin(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)
          AND ({tag_clause})
        ORDER BY ST_Distance(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)
        LIMIT :limit
        """
    )
    try:
        with engine.connect() as conn:
            if not _poi_available(conn):
                return None
            rows = conn.execute(sql, params).fetchall()
    except Exception as exc:  # DB/PostGIS problem -> let the caller use Overpass
        logger.warning("Local POI query failed, falling back to Overpass: %s", exc)
        return None
    return [_row_to_element(r) for r in rows]


def _demo() -> None:
    # ponytail check: the non-DB logic (clause building + row mapping) must hold.
    clause, params = _build_tag_clause([("shop", "supermarket"), ("amenity", "cafe")])
    assert clause == "tags ->> :k0 = :v0 OR tags ->> :k1 = :v1", clause
    assert params == {"k0": "shop", "v0": "supermarket", "k1": "amenity", "v1": "cafe"}, params
    assert _build_tag_clause([])[0] == "FALSE"

    class R:  # stand-in row
        osm_type, osm_id, lat, lon = "node", 42, 43.45, -80.49
        tags = '{"name": "T&T", "shop": "supermarket"}'
    el = _row_to_element(R())
    assert el == {"type": "node", "id": 42, "lat": 43.45, "lon": -80.49,
                  "tags": {"name": "T&T", "shop": "supermarket"}}, el
    print("poi_query_service demo OK")


if __name__ == "__main__":
    _demo()
