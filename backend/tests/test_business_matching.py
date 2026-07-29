"""Tests for mapping free-text business ideas to the nearest trained catalog type."""
from __future__ import annotations

from app.services.business_matching_service import map_idea_to_catalog_subcategory


def test_confident_matches_map_to_expected_subcategory():
    cases = {
        "cafe": "Coffee Shop / Cafe",
        "Tim Hortons": "Coffee Shop / Cafe",
        "boba tea": "Bubble Tea Shop",
        "phone repair shop": "Electronics Repair Shop",
        "a pizza place": "Pizza Shop",
        "yoga": "Yoga Studio",
        "Indian restaurant that serves paan": "Casual Restaurant",
        "pet store for cats": "Pet Supply Store",
    }
    for text, expected in cases.items():
        match = map_idea_to_catalog_subcategory(raw_text=text)
        assert match.subcategory == expected, f"{text!r} -> {match.subcategory!r}"
        assert match.basis == "nearest_catalog"
        assert match.is_confident, f"{text!r} should be confident"


def test_pure_nonsense_is_unavailable():
    match = map_idea_to_catalog_subcategory(raw_text="some random nonsense xyz")
    assert match.subcategory is None
    assert match.basis == "unavailable"
    assert not match.is_confident


def test_empty_input_is_unavailable():
    match = map_idea_to_catalog_subcategory(raw_text="")
    assert match.subcategory is None
    assert match.basis == "unavailable"


def test_low_confidence_match_is_labelled_but_flagged():
    # "gym" is a real signal (-> Fitness Center) but a single weak alias, so it is
    # returned as a nearest-catalog match while flagged as not high-confidence.
    match = map_idea_to_catalog_subcategory(raw_text="gym")
    assert match.subcategory == "Fitness Center"
    assert match.basis == "nearest_catalog"
    assert not match.is_confident
    assert "closest known business type" in match.label.lower()


def test_accepts_resolved_response_dict_signals():
    resolved = {
        "input_text": "spot to grab espresso",
        "normalized_business_name": "Espresso Bar",
        "primary_category": "coffee",
        "secondary_categories": ["cafe"],
        "brand_terms": [],
        "specialty_terms": ["espresso", "latte"],
    }
    match = map_idea_to_catalog_subcategory(resolved)
    assert match.subcategory == "Coffee Shop / Cafe"
    assert match.is_confident
