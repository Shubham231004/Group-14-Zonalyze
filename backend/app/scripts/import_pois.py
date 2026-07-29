"""Populate the local `poi` table (owned competitor/POI data) from a Geofabrik
OSM extract, using pyosmium. This is the owned, rate-limit-free source the app
queries instead of live Overpass (see poi_query_service).

Steps:
  1. Download an extract (province for a fast local test, Canada for production):
       Ontario: https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf
       Canada:  https://download.geofabrik.de/north-america/canada-latest.osm.pbf
  2. cd backend && python -m app.scripts.import_pois PATH\\to\\extract.osm.pbf
  3. Restart the backend so it picks up the store.

Re-run monthly to refresh.

ponytail: imports NODE POIs only — the bulk of competitors (shops, cafes,
restaurants, clinics, salons). Polygon POIs (supermarkets/malls drawn as
buildings) are skipped; add an osmium area handler with centroids if that gap
matters for the categories you care about.
"""

from __future__ import annotations

import sys

import osmium
import psycopg2.extras

from app.db.session import engine
from app.services.poi_query_service import POI_TAG_KEYS, create_poi_schema

_BATCH = 5000


class _PoiHandler(osmium.SimpleHandler):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.buf: list = []
        self.total = 0

    def node(self, n):
        if not n.location.valid():
            return
        # First matching key (in priority order) is the category; skip non-POI nodes
        # before building the full tag dict — most nodes have no POI tag.
        category = next((n.tags[k] for k in POI_TAG_KEYS if k in n.tags), None)
        if category is None:
            return
        tags = {t.k: t.v for t in n.tags}
        self.buf.append(
            ("node", n.id, tags.get("name"), category,
             psycopg2.extras.Json(tags), n.location.lat, n.location.lon)
        )
        if len(self.buf) >= _BATCH:
            self._flush()

    def _flush(self):
        if not self.buf:
            return
        with self.conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO poi (osm_type, osm_id, name, category, tags, lat, lon) "
                "VALUES %s ON CONFLICT (osm_type, osm_id) DO NOTHING",
                self.buf,
            )
        self.conn.commit()
        self.total += len(self.buf)
        self.buf = []
        print(f"  inserted {self.total:,}...", end="\r")


def main(pbf_path: str) -> None:
    print("Ensuring poi schema (PostGIS + table + index)...")
    create_poi_schema()
    print(f"Importing node POIs from {pbf_path} ...")
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cur:
            cur.execute("TRUNCATE poi")
        raw.commit()
        handler = _PoiHandler(raw)
        handler.apply_file(pbf_path)
        handler._flush()
        print(f"\nDone. Imported {handler.total:,} POIs. Restart the backend to use the store.")
    finally:
        raw.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m app.scripts.import_pois PATH\\to\\extract.osm.pbf")
    main(sys.argv[1])
