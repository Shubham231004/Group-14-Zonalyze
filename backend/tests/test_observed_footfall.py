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
