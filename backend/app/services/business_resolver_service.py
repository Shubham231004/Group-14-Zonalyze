from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.schemas.business_resolver import (
    BusinessResolveRequest,
    BusinessResolveResponse,
    OSMTagSuggestion,
)
from app.services.local_ai_service import generate_json_with_ollama
from app.services.business_resolution_cache_service import (
    get_cached_business_resolution,
    save_business_resolution_cache,
)


# TRUST RULE
# ----------
# No business-specific category mapping exists in this file.
# No brand list exists in this file.
# No keyword -> OSM tag mapping exists in this file.
#
# Local AI extracts business meaning and search phrases only.
# Final category tags must be discovered from OSM Taginfo and pass generic
# quality checks before they can drive map/competitor evidence.

MAX_TAGS = 10
MAX_TEXT_FIELD_LENGTH = 140
MAX_WARNING_COUNT = 8
MIN_TAGINFO_COUNT = int(os.getenv("OSM_TAGINFO_MIN_COUNT", "50"))
TAGINFO_TIMEOUT_SECONDS = float(os.getenv("OSM_TAGINFO_TIMEOUT_SECONDS", "8"))
TAGINFO_BASE_URL = os.getenv("OSM_TAGINFO_BASE_URL", "https://taginfo.openstreetmap.org").rstrip("/")

OSM_KEY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_:.-]{0,63}$")
OSM_VALUE_RE = re.compile(r"^[^\n\r\t]{1,120}$")
VALID_TAG_ROLES = {"primary", "secondary", "brand", "attribute", "name", "operator", "specialty", "other"}

# JSON schema for Ollama structured outputs — forces clean, well-typed resolver
# output (categories + search terms + candidate OSM tags) even on small models.
BUSINESS_RESOLVER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "normalized_business_name": {"type": "string"},
        "primary_category": {"type": "string"},
        "secondary_categories": {"type": "array", "items": {"type": "string"}},
        "brand_terms": {"type": "array", "items": {"type": "string"}},
        "specialty_terms": {"type": "array", "items": {"type": "string"}},
        "search_terms": {"type": "array", "items": {"type": "string"}},
        "osm_tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "confidence": {"type": "number"},
                    "tag_role": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
        "confidence_score": {"type": "number"},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["normalized_business_name", "primary_category", "search_terms"],
}

# Generic POI category keys only. This is not a business mapping; it only says
# which OSM keys are structurally useful as searchable POI/business categories.
SEARCHABLE_CATEGORY_KEYS = {
    "amenity",
    "shop",
    "craft",
    "office",
    "tourism",
    "leisure",
    "healthcare",
    "emergency",
    "railway",
    "public_transport",
    "man_made",
    "club",
    "sport",
}

# Descriptor/attribute keys can be useful for display/filtering, but they cannot
# be treated as the main business category.
DESCRIPTOR_ONLY_KEYS = {
    "brand",
    "operator",
    "name",
    "cuisine",
    "service",
    "fuel",
    "opening_hours",
    "website",
    "phone",
    "contact:phone",
    "contact:website",
    "payment",
    "addr:street",
    "addr:city",
}

GENERIC_INVALID_KEY_VALUE_PAIRS = {
    ("amenity", "shop"),
    ("shop", "amenity"),
    ("amenity", "business"),
    ("shop", "business"),
    ("service", ""),
    ("name", ""),
}

# These are generic English filler words that make Taginfo search noisy. This is
# not business mapping. It prevents broad queries like “station” from producing
# bus_station, bicycle_repair_station, etc.
GENERIC_SEARCH_WORDS = {
    "a", "an", "the", "and", "or", "with", "plus", "for", "near", "nearby",
    "business", "company", "location", "place", "service", "services",
    "store", "shop", "centre", "center", "station", "outlet", "retail",
}

# Some words are too ambiguous as single-token Taginfo searches. We only use them
# when they appear inside a longer phrase or when AI provides a cleaner synonym.
AMBIGUOUS_SINGLE_TOKEN_SEARCHES = {"gas", "auto", "car", "food", "retail"}


def _normalize_text(value: Any, max_length: int = MAX_TEXT_FIELD_LENGTH) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_length]


def _tokenize(value: str) -> list[str]:
    text = re.sub(r"[^a-zA-Z0-9_\s-]", " ", value or "").lower().replace("_", " ")
    tokens = [token.strip("- ") for token in re.split(r"\s+", text) if token.strip("- ")]
    normalized: list[str] = []
    for token in tokens:
        # Generic morphology only, not business mapping.
        if token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        normalized.append(token)
    return normalized


def _canonical_search_phrase(value: str) -> str:
    """
    Convert a phrase into a Taginfo search phrase while avoiding broad filler
    searches. Examples of generic cleanup: “convenience store” -> “convenience”,
    “fueling station” -> “fuel”. This is linguistic cleanup, not a business map.
    """
    tokens = _tokenize(value)
    useful = [token for token in tokens if token not in GENERIC_SEARCH_WORDS]

    if not useful:
        return ""

    # Avoid noisy single-token searches such as “gas” by itself.
    if len(useful) == 1 and useful[0] in AMBIGUOUS_SINGLE_TOKEN_SEARCHES:
        return ""

    # Keep phrases short. Taginfo search performs better with concise category-like terms.
    return " ".join(useful[:4])


def _normalize_role(value: Any) -> str:
    role = _normalize_text(value or "primary", 40).lower().replace(" ", "_")
    return role if role in VALID_TAG_ROLES else "other"


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    if score > 0:
        return "limited"
    return "unresolved"


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None

    return None


def _build_business_resolution_prompt(business_query: str) -> str:
    return f"""
Return ONLY valid JSON. No markdown. No explanation outside JSON.

You normalize a user-entered business idea for OpenStreetMap evidence lookup.
Do not estimate revenue, lease, risk, demand, or feasibility.
Do not invent local facts.

Your job:
1. Normalize the business meaning.
2. Separate brand/company names from the business category.
3. Provide concise search_terms for OSM Taginfo lookup.
4. search_terms should be category-like words or phrases likely to appear in OSM tag values or wiki text.
5. Do not put brand names in search_terms.
6. Do not use generic words alone such as station, store, shop, service, business, or place.
7. Optionally suggest OSM tags, but the backend will NOT trust them directly; they are only extra search clues.

Return this JSON shape exactly:
{{
  "normalized_business_name": "short plain-English business name",
  "primary_category": "plain-English primary business category",
  "secondary_categories": ["optional plain-English secondary categories"],
  "brand_terms": ["brand/company names explicitly mentioned by the user"],
  "specialty_terms": ["non-brand specialty descriptors"],
  "search_terms": ["concise category search phrases, no brands"],
  "osm_tags": [
    {{"key": "osm_key", "value": "osm_value", "confidence": 0.0, "tag_role": "primary|secondary|brand|attribute|name|operator|specialty|other", "reason": "brief reason"}}
  ],
  "confidence_score": 0.0,
  "warnings": ["uncertainties or coverage limitations"]
}}

User business idea: {business_query}
""".strip()


def _clean_text_list(value: Any, max_items: int = 8) -> List[str]:
    if not isinstance(value, list):
        return []
    cleaned: List[str] = []
    seen: set[str] = set()
    for item in value[:max_items]:
        text = _normalize_text(item)
        key = text.lower()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _is_tag_shape_valid(key: str, value: str) -> Tuple[bool, Optional[str]]:
    if not key or not value:
        return False, "Missing tag key or value."
    if not OSM_KEY_RE.match(key):
        return False, f"Invalid OSM key format: {key}"
    if not OSM_VALUE_RE.match(value):
        return False, "Invalid OSM value format."
    if (key, value.lower()) in GENERIC_INVALID_KEY_VALUE_PAIRS:
        return False, f"Generic OSM tag mismatch: {key}={value}."
    return True, None


def _is_usable_category_key(key: str) -> bool:
    return key in SEARCHABLE_CATEGORY_KEYS and key not in DESCRIPTOR_ONLY_KEYS


def _taginfo_get(path: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        response = requests.get(
            f"{TAGINFO_BASE_URL}{path}",
            params=params,
            timeout=TAGINFO_TIMEOUT_SECONDS,
            headers={"User-Agent": "Zonalyze-Capstone/1.0 OSM tag resolver"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _tag_count_from_overview(key: str, value: str) -> int:
    payload = _taginfo_get("/api/4/tag/overview", {"key": key, "value": value})
    if not payload:
        return 0
    data = payload.get("data") or {}
    try:
        return int(data.get("count_all") or data.get("count") or 0)
    except Exception:
        return 0


def _taginfo_search(query: str) -> List[Dict[str, Any]]:
    """Search Taginfo dynamically using a cleaned category phrase."""
    results: List[Dict[str, Any]] = []
    query = _normalize_text(query, 80)
    if not query:
        return results

    endpoints = [
        ("/api/4/search/by_value", {"query": query, "rp": 25, "page": 1}),
        ("/api/4/search/by_keyword", {"query": query, "rp": 25, "page": 1}),
        ("/api/4/tags/popular", {"query": query, "rp": 25, "page": 1}),
    ]
    for path, params in endpoints:
        payload = _taginfo_get(path, params)
        if payload and isinstance(payload.get("data"), list):
            results.extend(payload.get("data") or [])

    return results


def _count_score(count: int) -> float:
    if count <= 0:
        return 0.0
    return min(0.95, 0.35 + (math.log10(count + 1) / 8.0))


def _candidate_score(item: Dict[str, Any], query: str) -> float:
    key = _normalize_text(item.get("key"), 64).lower()
    value = _normalize_text(item.get("value"), 120).lower()
    ok, _ = _is_tag_shape_valid(key, value)
    if not ok or not _is_usable_category_key(key):
        return -1

    count = 0
    for count_key in ("count_all", "count", "count_nodes", "count_ways", "count_relations"):
        try:
            count = max(count, int(item.get(count_key) or 0))
        except Exception:
            pass
    if count <= 0:
        count = _tag_count_from_overview(key, value)
    if count < MIN_TAGINFO_COUNT:
        return -1

    query_tokens = set(_tokenize(query)) - GENERIC_SEARCH_WORDS - AMBIGUOUS_SINGLE_TOKEN_SEARCHES
    value_tokens = set(_tokenize(value)) - GENERIC_SEARCH_WORDS

    if not query_tokens or not value_tokens:
        return -1

    query_l = " ".join(sorted(query_tokens))
    value_l = " ".join(sorted(value_tokens))

    score = 0.0
    if value.replace("_", " ") == query.lower():
        score += 220
    elif value_l == query_l:
        score += 190
    elif value_tokens & query_tokens:
        score += 110 * (len(value_tokens & query_tokens) / max(1, len(query_tokens)))
    else:
        return -1

    if key in {"amenity", "shop", "craft", "office", "healthcare"}:
        score += 30
    elif key in SEARCHABLE_CATEGORY_KEYS:
        score += 15

    score += min(25, math.log10(count + 1) * 3)
    return score


def _candidate_from_taginfo(item: Dict[str, Any], query: str, role: str) -> Optional[OSMTagSuggestion]:
    score = _candidate_score(item, query)
    if score < 100:
        return None

    key = _normalize_text(item.get("key"), 64).lower()
    value = _normalize_text(item.get("value"), 120)

    count = 0
    for count_key in ("count_all", "count", "count_nodes", "count_ways", "count_relations"):
        try:
            count = max(count, int(item.get(count_key) or 0))
        except Exception:
            pass
    if count <= 0:
        count = _tag_count_from_overview(key, value)

    confidence = max(0.55, min(0.95, (score / 260) * 0.75 + _count_score(count) * 0.25))
    return OSMTagSuggestion(
        key=key,
        value=value,
        confidence=round(confidence, 3),
        tag_role=role,
        reason=f"Verified by OSM Taginfo search for '{query}' with about {count:,} uses.",
    )


def _merge_tag(tag: OSMTagSuggestion, by_pair: Dict[Tuple[str, str], OSMTagSuggestion]) -> None:
    pair = (tag.key.lower(), tag.value.lower())
    existing = by_pair.get(pair)
    if not existing or tag.confidence > existing.confidence:
        by_pair[pair] = tag


def _build_taginfo_search_terms(payload: Dict[str, Any], business_query: str) -> List[str]:
    raw_terms: List[str] = []
    raw_terms += _clean_text_list(payload.get("search_terms"), 10)
    raw_terms += _clean_text_list([payload.get("primary_category")], 1)
    raw_terms += _clean_text_list(payload.get("secondary_categories"), 5)
    raw_terms += _clean_text_list(payload.get("specialty_terms"), 5)

    # AI tag suggestions are not trusted directly, but their values/reasons can
    # contain useful category phrases like “fueling station” or “convenience store”.
    raw_tags = payload.get("osm_tags") or []
    if isinstance(raw_tags, list):
        for raw in raw_tags[:MAX_TAGS]:
            if isinstance(raw, dict):
                raw_terms.append(_normalize_text(raw.get("value"), 80))
                raw_terms.append(_normalize_text(raw.get("reason"), 100))

    # The original query is only useful if cleanup produces non-generic terms.
    raw_terms.append(business_query)

    brands = _clean_text_list(payload.get("brand_terms"), 8)
    final_terms: List[str] = []
    seen: set[str] = set()

    for term in raw_terms:
        cleaned = term
        for brand in brands:
            cleaned = re.sub(re.escape(brand), " ", cleaned, flags=re.IGNORECASE)

        # Split compounds but never keep generic-only fragments.
        parts = re.split(r"\b(?:with|and|plus|&|\+)\b", cleaned, flags=re.IGNORECASE)
        for part in parts:
            canonical = _canonical_search_phrase(part)
            if canonical and canonical.lower() not in seen:
                final_terms.append(canonical)
                seen.add(canonical.lower())

    return final_terms[:10]


def _discover_category_tags(payload: Dict[str, Any], business_query: str) -> Tuple[List[OSMTagSuggestion], List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    rejected: List[Dict[str, Any]] = []
    by_pair: Dict[Tuple[str, str], OSMTagSuggestion] = {}

    search_terms = _build_taginfo_search_terms(payload, business_query)

    for index, term in enumerate(search_terms):
        taginfo_items = _taginfo_search(term)
        local_matches = 0
        for item in taginfo_items:
            role = "primary" if index == 0 else "secondary"
            tag = _candidate_from_taginfo(item, query=term, role=role)
            if tag:
                _merge_tag(tag, by_pair)
                local_matches += 1
            elif len(rejected) < 40:
                rejected.append(
                    {
                        "raw": {
                            "key": item.get("key"),
                            "value": item.get("value"),
                            "count_all": item.get("count_all") or item.get("count"),
                            "query": term,
                        },
                        "reason": "Taginfo result failed strict semantic/category validation.",
                    }
                )

        # One good match from a strong first term is often enough; keep searching
        # secondary terms too, but do not let noisy generic terms dominate.
        if index == 0 and local_matches == 0:
            warnings.append(f"No strong Taginfo category match found for primary search term '{term}'.")

    category_tags = sorted(by_pair.values(), key=lambda tag: (tag.tag_role != "primary", -tag.confidence))[:6]

    if not category_tags:
        warnings.append(
            "Taginfo did not return a strong searchable OSM category tag for the AI-extracted business terms."
        )

    return category_tags, rejected, warnings


def _validate_ai_descriptor_tags(raw_tags: Any) -> Tuple[List[OSMTagSuggestion], List[Dict[str, Any]]]:
    accepted: List[OSMTagSuggestion] = []
    rejected: List[Dict[str, Any]] = []

    if not isinstance(raw_tags, list):
        return accepted, rejected

    for raw in raw_tags[:MAX_TAGS]:
        if not isinstance(raw, dict):
            rejected.append({"raw": raw, "reason": "Tag suggestion was not an object."})
            continue
        key = _normalize_text(raw.get("key"), 64).lower()
        value = _normalize_text(raw.get("value"), 120)
        role = _normalize_role(raw.get("tag_role"))
        reason = _normalize_text(raw.get("reason"), 180) or None
        try:
            confidence = max(0.0, min(1.0, float(raw.get("confidence", 0.5))))
        except Exception:
            confidence = 0.5

        ok, reject_reason = _is_tag_shape_valid(key, value)
        if not ok:
            rejected.append({"raw": raw, "reason": reject_reason})
            continue

        if role in {"primary", "secondary"} or key in SEARCHABLE_CATEGORY_KEYS:
            rejected.append({
                "raw": raw,
                "reason": "AI category tag was not accepted directly; category tags must be verified through Taginfo search.",
            })
            continue

        accepted.append(OSMTagSuggestion(
            key=key,
            value=value,
            confidence=round(confidence, 3),
            tag_role=role,
            reason=reason or "AI-extracted descriptor tag; not used as primary category evidence.",
        ))

    return accepted, rejected


def _needs_review_response(
    *,
    business_query: str,
    source_method: str,
    warning: str,
    raw_ai_error: Optional[str] = None,
    rejected_osm_tags: Optional[List[Dict[str, Any]]] = None,
) -> BusinessResolveResponse:
    return BusinessResolveResponse(
        status="needs_review",
        input_text=business_query,
        normalized_business_name="",
        primary_category="",
        secondary_categories=[],
        brand_terms=[],
        specialty_terms=[],
        osm_tags=[],
        rejected_osm_tags=rejected_osm_tags or [],
        resolution_confidence="unresolved",
        confidence_score=0.0,
        source_method=source_method,
        raw_ai_available=False,
        warnings=[warning],
        next_steps=[
            "Confirm the local Ollama model is running and returns structured business meaning.",
            "Confirm the machine has internet access for OSM Taginfo validation.",
            "Do not run competitor evidence for this business until OSM tags are resolved.",
        ],
        raw_ai_error=raw_ai_error,
    )


def _coerce_ai_payload(payload: Dict[str, Any], business_query: str) -> Dict[str, Any]:
    return {
        "normalized_business_name": _normalize_text(payload.get("normalized_business_name")) or business_query,
        "primary_category": _normalize_text(payload.get("primary_category")) or "Unresolved business category",
        "secondary_categories": _clean_text_list(payload.get("secondary_categories")),
        "brand_terms": _clean_text_list(payload.get("brand_terms")),
        "specialty_terms": _clean_text_list(payload.get("specialty_terms")),
        "search_terms": _clean_text_list(payload.get("search_terms"), 10),
        "osm_tags": payload.get("osm_tags") or [],
        "confidence_score": payload.get("confidence_score", 0.0),
        "warnings": _clean_text_list(payload.get("warnings"), MAX_WARNING_COUNT),
    }


def resolve_business_query(request: BusinessResolveRequest) -> BusinessResolveResponse:
    business_query = _normalize_text(request.business_query, 240)

    if not business_query:
        return _needs_review_response(
            business_query=str(request.business_query or ""),
            source_method="input_validation_failed",
            warning="Business query was empty. Enter a business idea before resolving OSM tags.",
        )

    cached_response = get_cached_business_resolution(
        business_query=business_query,
        model=request.model,
    )
    if cached_response is not None:
        return cached_response

    prompt = _build_business_resolution_prompt(business_query)
    ai_result = generate_json_with_ollama(
        prompt=prompt,
        model=request.model,
        timeout_seconds=90,
        json_schema=BUSINESS_RESOLVER_JSON_SCHEMA,
    )

    if not ai_result.available:
        return _needs_review_response(
            business_query=business_query,
            source_method="local_ai_unavailable_no_fallback_category_mapping",
            warning=(
                "Local AI did not return a structured business interpretation. Zonalyze did not guess "
                "business categories, brands, or OSM tags because hardcoded category fallback is disabled."
            ),
            raw_ai_error=ai_result.error,
        )

    raw_payload = _extract_json_object(ai_result.answer)
    if not raw_payload:
        return _needs_review_response(
            business_query=business_query,
            source_method="local_ai_invalid_json_no_fallback_category_mapping",
            warning=(
                "Local AI returned text, but not valid structured JSON. Zonalyze did not guess "
                "business categories or OSM tags because hardcoded category fallback is disabled."
            ),
            raw_ai_error="Local AI response was not valid JSON.",
        )

    payload = _coerce_ai_payload(raw_payload, business_query)

    category_tags, category_rejections, category_warnings = _discover_category_tags(payload, business_query)
    descriptor_tags, descriptor_rejections = _validate_ai_descriptor_tags(payload.get("osm_tags"))

    rejected_tags = category_rejections + descriptor_rejections
    warnings = list(payload.get("warnings") or []) + category_warnings

    try:
        ai_confidence = float(payload.get("confidence_score", 0.0))
    except Exception:
        ai_confidence = 0.0
    ai_confidence = max(0.0, min(1.0, ai_confidence))

    if not category_tags:
        return _needs_review_response(
            business_query=business_query,
            source_method="local_ai_meaning_extracted_but_taginfo_unresolved",
            warning=(
                "Local AI extracted business meaning, but OSM Taginfo did not verify a strong searchable "
                "category tag. Zonalyze did not invent replacement tags because hardcoded OSM mappings are disabled."
            ),
            raw_ai_error=None,
            rejected_osm_tags=rejected_tags,
        )

    final_tags = category_tags[:6] + descriptor_tags[:4]
    best_category_confidence = max((tag.confidence for tag in category_tags), default=0.0)
    confidence_score = max(0.0, min(1.0, (best_category_confidence * 0.75) + (ai_confidence * 0.25)))

    next_steps = [
        "Show this business interpretation and the OSM tags to the user before running full analysis.",
        "Use Taginfo-verified category tags for competitor and market-map evidence.",
        "Verify tag coverage with Overpass result counts before treating competitor evidence as strong.",
    ]

    if confidence_score < 0.45:
        next_steps.append("Ask the user to clarify the business idea or confirm the resolved category.")

    response = BusinessResolveResponse(
        status="resolved",
        input_text=business_query,
        normalized_business_name=payload.get("normalized_business_name") or business_query,
        primary_category=payload.get("primary_category") or "Unresolved business category",
        secondary_categories=payload.get("secondary_categories") or [],
        brand_terms=payload.get("brand_terms") or [],
        specialty_terms=payload.get("specialty_terms") or [],
        osm_tags=final_tags[:MAX_TAGS],
        rejected_osm_tags=rejected_tags[:40],
        resolution_confidence=_confidence_label(confidence_score),
        confidence_score=round(confidence_score, 3),
        source_method="local_ai_meaning_plus_osm_taginfo_verified_tags",
        raw_ai_available=True,
        warnings=list(dict.fromkeys([warning for warning in warnings if warning]))[:MAX_WARNING_COUNT],
        next_steps=next_steps,
        raw_ai_error=None,
    )

    save_business_resolution_cache(
        business_query=business_query,
        model=request.model,
        response=response,
    )

    return response
