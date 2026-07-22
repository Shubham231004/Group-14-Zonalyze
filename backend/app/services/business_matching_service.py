"""Map a free-text business idea to the nearest trained catalog subcategory.

The ML feasibility model is only trained on the ~26 catalog subcategories. When a
user types a free-text idea (e.g. "artisan candle bar", "Tim Hortons", "Indian
restaurant that serves paan"), this service finds the closest trained type so the
app can still show a feasibility score -- clearly labelled as an approximation --
or honestly report that no confident match exists.

It reuses the curated alias tables already maintained for competitor matching
(osm_service.COMPETITOR_RULES) rather than inventing a second keyword table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.catalogs.business_subcategories import list_business_subcategory_options
from app.services.osm_service import COMPETITOR_RULES


# Scoring weights. Alias hits are the strongest signal because the alias tables are
# curated per business type (brands, keywords). A multi-word alias (e.g. a brand
# like "tim hortons") is stronger still than a single generic word.
_PHRASE_ALIAS_SCORE = 4
_WORD_ALIAS_SCORE = 3
_NAME_TOKEN_SCORE = 2
# Category names ("Food Service", "Retail") are too broad to score on -- they cause
# cross-matches like "dog food store" -> a restaurant category. Intentionally unused.

_MIN_MATCH_SCORE = 3      # below this, we report "unavailable" rather than guess
_CONFIDENT_SCORE = 4      # at/above this the match is treated as high-confidence

# Words too generic to carry business meaning when tokenizing a subcategory name.
_STOPWORDS = {
    "a", "an", "the", "of", "for", "to", "in", "on", "at", "by", "with", "and",
    "shop", "store", "center", "centre", "service", "services",
}


@dataclass(frozen=True)
class CatalogMatch:
    subcategory: Optional[str]
    confidence: float
    is_confident: bool
    basis: str  # "nearest_catalog" | "unavailable"
    label: str


def _clean(text: object) -> str:
    value = str(text or "").lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9+ ]+", " ", value)
    return " ".join(value.split())


def _name_tokens(text: str) -> List[str]:
    return [word for word in _clean(text).split() if len(word) >= 3 and word not in _STOPWORDS]


def _contains(haystack: str, needle: str) -> bool:
    clean_needle = _clean(needle)
    if not clean_needle:
        return False
    if " " in clean_needle:
        return clean_needle in haystack
    return re.search(rf"(?:^| ){re.escape(clean_needle)}(?:$| )", haystack) is not None


def _signal_text(resolved: object, raw_text: str) -> str:
    """Collect every text signal from a resolved business idea (or raw text)."""
    parts: List[str] = [raw_text or ""]

    def _get(attr: str):
        if resolved is None:
            return None
        if isinstance(resolved, dict):
            return resolved.get(attr)
        return getattr(resolved, attr, None)

    for attr in ("input_text", "normalized_business_name", "primary_category"):
        parts.append(str(_get(attr) or ""))
    for attr in ("secondary_categories", "brand_terms", "specialty_terms"):
        value = _get(attr) or []
        if isinstance(value, (list, tuple)):
            parts.extend(str(item) for item in value)
    return _clean(" ".join(parts))


_OPTIONS_CACHE: Optional[List[Tuple[str, str]]] = None


def _subcategory_category_pairs() -> List[Tuple[str, str]]:
    global _OPTIONS_CACHE
    if _OPTIONS_CACHE is None:
        _OPTIONS_CACHE = [
            (opt["business_subcategory"], opt["business_category"])
            for opt in list_business_subcategory_options()
        ]
    return _OPTIONS_CACHE


def map_idea_to_catalog_subcategory(resolved: object = None, *, raw_text: str = "") -> CatalogMatch:
    """Return the nearest trained catalog subcategory for a free-text business idea.

    `resolved` is an optional BusinessResolveResponse (or dict) from the AI resolver;
    `raw_text` is the user's original text. Either or both may be supplied.
    """
    signals = _signal_text(resolved, raw_text)
    if not signals:
        return CatalogMatch(None, 0.0, False, "unavailable", "No business input was provided to score.")

    best_subcategory: Optional[str] = None
    best_score = 0

    for subcategory, _category in _subcategory_category_pairs():
        rule = COMPETITOR_RULES.get(subcategory.lower().strip())
        aliases = rule.aliases if rule else ()

        score = 0
        for alias in aliases:
            if _contains(signals, alias):
                score += _PHRASE_ALIAS_SCORE if " " in _clean(alias) else _WORD_ALIAS_SCORE
        for token in _name_tokens(subcategory):
            if _contains(signals, token):
                score += _NAME_TOKEN_SCORE

        if score > best_score:
            best_score = score
            best_subcategory = subcategory

    if best_subcategory is None or best_score < _MIN_MATCH_SCORE:
        return CatalogMatch(
            None,
            0.0,
            False,
            "unavailable",
            "This idea does not clearly match a trained business type, so no feasibility score is shown.",
        )

    confidence = round(max(0.0, min(1.0, best_score / 6.0)), 3)
    is_confident = best_score >= _CONFIDENT_SCORE
    qualifier = "" if is_confident else " (low confidence — treat as a rough guide)"
    label = f"Feasibility based on the closest known business type: {best_subcategory}{qualifier}."
    return CatalogMatch(best_subcategory, confidence, is_confident, "nearest_catalog", label)
