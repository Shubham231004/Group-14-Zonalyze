from app.services import footfall_heatmap_service
from app.services.footfall_heatmap_service import build_footfall_heatmap_points


def test_footfall_heatmap_uses_observed_counter_values_inside_radius():
    points = build_footfall_heatmap_points(
        center_lat=43.443488819,
        center_lng=-80.496073865,
        radius_km=0.25,
    )

    assert len(points) == 1
    assert points[0].point_id == "observed-counter-kitchener-100021132"
    assert points[0].observed_count == 423
    assert points[0].observed_unit == "average pedestrians/day"
    assert points[0].evidence_type == "observed_pedestrian_count"


def test_footfall_heatmap_does_not_invent_points_without_counter_coverage():
    assert build_footfall_heatmap_points(
        center_lat=43.3616,
        center_lng=-80.3144,
        radius_km=2,
    ) == []


def test_footfall_heatmap_has_observed_coverage_outside_waterloo_region():
    test_locations = (
        (43.6532, -79.3832, "City of Toronto"),
        (44.3894, -79.6903, "City of Barrie"),
        (43.2557, -79.8711, "City of Hamilton"),
        (44.2489, -76.9507, "County of Lennox and Addington"),
    )

    for latitude, longitude, expected_source in test_locations:
        points = build_footfall_heatmap_points(
            center_lat=latitude,
            center_lng=longitude,
            radius_km=12,
        )
        assert points, expected_source
        assert any(expected_source in point.source for point in points)


def test_footfall_heatmap_is_safe_when_snapshot_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        footfall_heatmap_service,
        "DATA_PATH",
        tmp_path / "missing-footfall.csv",
    )

    assert build_footfall_heatmap_points(
        center_lat=43.6532,
        center_lng=-79.3832,
        radius_km=2,
    ) == []
