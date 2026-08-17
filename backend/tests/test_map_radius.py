from app.schemas.geospatial import GeospatialMarketRequest
from app.services import geospatial_service
from app.services.osm_service import OSMFetchResult, build_overpass_query


def test_larger_radius_returns_additional_competitor_markers(monkeypatch):
    def competitors_for_radius(*, radius_km, **_):
        return OSMFetchResult(
            status="live_osm",
            note="test data",
            elements=[
                {
                    "osm_id": str(index),
                    "osm_type": "node",
                    "name": f"Competitor {index}",
                    "latitude": 43.4516 + index * 0.00001,
                    "longitude": -80.4925,
                    "category": "Coffee Shop",
                    "address": None,
                    "tags": {},
                }
                for index in range(int(radius_km * 10))
            ],
        )

    empty_osm = lambda **_: OSMFetchResult(status="live_osm", note="test data", elements=[])
    monkeypatch.setattr(geospatial_service, "fetch_osm_competitors", competitors_for_radius)
    monkeypatch.setattr(geospatial_service, "fetch_osm_transit", empty_osm)
    monkeypatch.setattr(geospatial_service, "enrich_missing_addresses", lambda elements, **_: elements)
    monkeypatch.setattr(geospatial_service, "build_prediction_features", lambda **_: {})
    monkeypatch.setattr(geospatial_service, "get_competition_observation", lambda **_: None)
    monkeypatch.setattr(geospatial_service, "get_demand_evidence", lambda **_: None)
    monkeypatch.setattr(geospatial_service, "get_lease_cost_evidence", lambda **_: None)
    monkeypatch.setattr(geospatial_service, "build_osm_competition_evidence", lambda **_: None)
    monkeypatch.setattr(geospatial_service, "build_footfall_heatmap_points", lambda **_: [])

    def context(radius_km):
        return geospatial_service.build_geospatial_market_context(
            GeospatialMarketRequest(
                municipality_name="Kitchener",
                business_subcategory="Coffee Shop",
                radius_km=radius_km,
            )
        )

    assert context(4).real_competitor_count == 40
    assert context(6).real_competitor_count == 60


def test_overpass_radius_matches_the_25_km_ui_limit():
    query = build_overpass_query([("amenity", "cafe")], 43.4516, -80.4925, 25)
    assert "around:25000" in query
