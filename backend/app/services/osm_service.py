from __future__ import annotations

import json
import logging
import math
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from app.catalogs.business_subcategories import get_business_profile_dict, get_osm_tags_for_subcategory
from app.services import poi_query_service

logger = logging.getLogger("zonalyze.osm")


# Public Overpass endpoints tried in order. The main de server rate-limits and
# times out often, so we fall back to community mirrors before giving up.
# Override/extend via OVERPASS_ENDPOINTS (comma-separated).
_DEFAULT_OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)


def _overpass_endpoints() -> List[str]:
    raw = os.getenv("OVERPASS_ENDPOINTS", "").strip()
    if raw:
        endpoints = [e.strip() for e in raw.split(",") if e.strip()]
        if endpoints:
            return endpoints
    return list(_DEFAULT_OVERPASS_ENDPOINTS)


# Kept for backward compatibility (first/primary endpoint).
OVERPASS_URL = _DEFAULT_OVERPASS_ENDPOINTS[0]
# Bounded so that, even if every mirror in the failover chain times out, the
# three market-map queries (run in parallel by geospatial_service) stay well
# under the frontend's 60s request timeout. Override via env if needed.
OVERPASS_TIMEOUT_SECONDS = int(os.getenv("OVERPASS_TIMEOUT_SECONDS", "12"))
CACHE_TTL_SECONDS = 60 * 60 * 6
# A failed lookup is only cached briefly, so a transient Overpass outage does not
# blank the map for hours (the previous behavior cached failures for 6h).
FAILURE_CACHE_TTL_SECONDS = int(os.getenv("OVERPASS_FAILURE_CACHE_SECONDS", "45"))


@dataclass
class OSMFetchResult:
    status: str
    note: str
    elements: List[Dict]


@dataclass(frozen=True)
class CompetitorRule:
    """Business-specific relevance settings used by the universal matcher.

    The matcher does not depend on one business such as Indian Grocery Store.
    Every selected business goes through the same scoring pipeline:
    1. OSM tag fit
    2. business/name/tag keyword fit
    3. rejection of unrelated nearby businesses
    4. minimum relevance threshold
    """

    aliases: Tuple[str, ...] = ()
    strong_tags: Tuple[Tuple[str, str], ...] = ()
    weak_tags: Tuple[Tuple[str, str], ...] = ()
    reject_terms: Tuple[str, ...] = ()
    min_score: int = 45
    weak_tag_requires_alias: bool = True


_CACHE: Dict[str, Tuple[float, OSMFetchResult]] = {}

# --- Disk-backed Overpass cache + circuit breaker (Step B: reliability) -------
# Public Overpass is frequently blocked/throttled (campus networks especially).
# Successful results are persisted to disk so competitors load instantly, survive
# restarts, and can be served *stale* when the live API is unreachable — far
# better than a blank map. Prefetch on a working network with
# `python -m app.scripts.prefetch_overpass_cache`.
_DISK_CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "generated" / "overpass_cache.json"
DISK_CACHE_MAX_ENTRIES = int(os.getenv("OVERPASS_DISK_CACHE_MAX_ENTRIES", "3000"))
# Socket timeout per endpoint attempt. MUST be greater than the server-side query
# budget (OVERPASS_TIMEOUT_SECONDS) or the client hangs up before Overpass can
# answer — which shows up as "read operation timed out" on queries that would have
# succeeded. Kept modest so a fully-dead mirror still fails over reasonably fast.
OVERPASS_HTTP_TIMEOUT_SECONDS = int(os.getenv("OVERPASS_HTTP_TIMEOUT_SECONDS", "16"))

# Circuit breaker: after several consecutive live failures, skip the network for a
# short cooldown so requests return instantly (from cache) instead of hanging every
# time. Tuned to tolerate transient blips on a working network (so live address
# typing keeps working) while still protecting a fully-blocked network.
_CIRCUIT_FAIL_THRESHOLD = int(os.getenv("OVERPASS_CIRCUIT_FAIL_THRESHOLD", "3"))
_CIRCUIT_COOLDOWN_SECONDS = int(os.getenv("OVERPASS_CIRCUIT_COOLDOWN_SECONDS", "30"))
_circuit = {"failures": 0, "open_until": 0.0}


def _load_disk_cache() -> None:
    try:
        if not _DISK_CACHE_PATH.exists():
            return
        raw = json.loads(_DISK_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read Overpass disk cache: %s", exc)
        return
    for key, entry in (raw.get("entries") or {}).items():
        try:
            _CACHE[key] = (
                float(entry["cached_at"]),
                OSMFetchResult(
                    status=entry.get("status", "live_osm"),
                    note=entry.get("note", ""),
                    elements=entry.get("elements", []),
                ),
            )
        except Exception:  # noqa: BLE001
            continue


def _save_disk_cache() -> None:
    try:
        _DISK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Persist only genuine OSM results (never transient failures), newest first, capped.
        items = [(key, ts, res) for key, (ts, res) in _CACHE.items() if res.status == "live_osm"]
        items.sort(key=lambda item: item[1], reverse=True)
        entries = {
            key: {"cached_at": ts, "status": res.status, "note": res.note, "elements": res.elements}
            for key, ts, res in items[:DISK_CACHE_MAX_ENTRIES]
        }
        _DISK_CACHE_PATH.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not write Overpass disk cache: %s", exc)


_load_disk_cache()


# These terms are intentionally broad. They are used only for text normalization,
# not as business filters.
GENERIC_BUSINESS_WORDS = {
    "a", "an", "and", "the", "of", "for", "to", "in", "on", "at", "by", "with",
    "store", "shop", "center", "centre", "business", "service", "services", "retail",
    "clinic", "restaurant", "cafe", "coffee", "food", "market", "mart", "studio",
}

COMMON_UNRELATED_FOR_FOOD_RETAIL = (
    "circle k", "7 eleven", "7-eleven", "esso", "shell", "petro", "canadian tire gas",
    "gas station", "fuel", "hasty market", "daisy mart", "dollarama", "dollar tree",
)

COMMON_UNRELATED_FOR_RESTAURANTS = (
    "gas station", "fuel", "convenience", "grocery", "supermarket", "pharmacy", "dollarama",
)


# Universal competitor rule table for the subcategories currently supported by Zonalyze.
# This is not a one-off filter. It gives every business type its own definition of what a
# close competitor looks like, while the matching algorithm remains the same for all types.
COMPETITOR_RULES: Dict[str, CompetitorRule] = {
    "indian grocery store": CompetitorRule(
        aliases=("indian", "india", "desi", "punjabi", "south asian", "asian", "spice", "spices", "masala", "halal", "bazaar", "mandi"),
        strong_tags=(("shop", "spices"), ("shop", "greengrocer"), ("shop", "supermarket")),
        weak_tags=(("shop", "convenience"),),
        reject_terms=COMMON_UNRELATED_FOR_FOOD_RETAIL,
        min_score=55,
    ),
    "chinese grocery store": CompetitorRule(
        aliases=("chinese", "china", "asian", "oriental", "t&t", "seafood", "supermarket", "grocery", "foods"),
        strong_tags=(("shop", "supermarket"), ("shop", "greengrocer")),
        weak_tags=(("shop", "convenience"),),
        reject_terms=COMMON_UNRELATED_FOR_FOOD_RETAIL,
        min_score=55,
    ),
    "halal grocery store": CompetitorRule(
        aliases=("halal", "middle eastern", "arab", "islamic", "butcher", "meat", "grocery", "foods", "market"),
        strong_tags=(("shop", "butcher"), ("shop", "supermarket"), ("shop", "greengrocer")),
        weak_tags=(("shop", "convenience"),),
        reject_terms=COMMON_UNRELATED_FOR_FOOD_RETAIL,
        min_score=55,
    ),
    "general grocery store": CompetitorRule(
        aliases=("grocery", "grocer", "supermarket", "food basics", "sobeys", "zehrs", "freshco", "no frills", "market", "foods"),
        strong_tags=(("shop", "supermarket"), ("shop", "greengrocer")),
        weak_tags=(("shop", "convenience"),),
        reject_terms=("gas station", "fuel", "esso", "shell", "circle k", "7-eleven"),
        min_score=48,
    ),
    "convenience store": CompetitorRule(
        aliases=("convenience", "variety", "corner store", "circle k", "7-eleven", "hasty market", "daisy mart"),
        strong_tags=(("shop", "convenience"),),
        weak_tags=(),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "coffee shop / cafe": CompetitorRule(
        aliases=("coffee", "cafe", "café", "espresso", "latte", "starbucks", "tim hortons", "second cup"),
        strong_tags=(("amenity", "cafe"),),
        weak_tags=(),
        reject_terms=("restaurant", "bar", "pub", "gas station"),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "bubble tea shop": CompetitorRule(
        aliases=("bubble tea", "boba", "milk tea", "tea", "chatime", "coco", "gong cha", "the alley"),
        strong_tags=(("shop", "tea"),),
        weak_tags=(("amenity", "cafe"),),
        reject_terms=("coffee", "tim hortons", "starbucks", "restaurant", "bar"),
        min_score=55,
    ),
    "fast food restaurant": CompetitorRule(
        aliases=("fast food", "burger", "fried chicken", "mcdonald", "wendy", "subway", "kfc", "popeyes", "harvey", "a&w", "taco bell"),
        strong_tags=(("amenity", "fast_food"),),
        weak_tags=(),
        reject_terms=("grocery", "supermarket", "pharmacy"),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "casual restaurant": CompetitorRule(
        aliases=("restaurant", "grill", "kitchen", "diner", "bistro", "bar", "pub", "eatery", "food"),
        strong_tags=(("amenity", "restaurant"),),
        weak_tags=(),
        reject_terms=("grocery", "supermarket", "pharmacy", "gas station"),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "pizza shop": CompetitorRule(
        aliases=("pizza", "pizzeria", "domino", "pizza pizza", "little caesars", "papa john", "241 pizza"),
        strong_tags=(),
        weak_tags=(("amenity", "restaurant"), ("amenity", "fast_food")),
        reject_terms=COMMON_UNRELATED_FOR_RESTAURANTS,
        min_score=55,
    ),
    "bakery": CompetitorRule(
        aliases=("bakery", "bake", "bread", "cakes", "pastry", "patisserie", "dessert"),
        strong_tags=(("shop", "bakery"),),
        weak_tags=(),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "fitness center": CompetitorRule(
        aliases=("fitness", "gym", "health club", "workout", "goodlife", "fit4less", "planet fitness", "anytime fitness"),
        strong_tags=(("leisure", "fitness_centre"), ("amenity", "gym")),
        weak_tags=(),
        reject_terms=("playground", "park", "school"),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "yoga studio": CompetitorRule(
        aliases=("yoga", "pilates", "hot yoga", "wellness studio"),
        strong_tags=(("sport", "yoga"),),
        weak_tags=(("leisure", "fitness_centre"),),
        reject_terms=("gym", "crossfit", "boxing", "martial arts"),
        min_score=55,
    ),
    "physiotherapy clinic": CompetitorRule(
        aliases=("physio", "physiotherapy", "physical therapy", "rehab", "rehabilitation", "sports medicine"),
        strong_tags=(("healthcare", "physiotherapist"),),
        weak_tags=(("amenity", "clinic"),),
        reject_terms=("dental", "dentist", "pharmacy", "walk-in", "family doctor", "veterinary"),
        min_score=55,
    ),
    "pharmacy": CompetitorRule(
        aliases=("pharmacy", "drug mart", "chemist", "shoppers", "rexall", "pharmasave", "guardian"),
        strong_tags=(("amenity", "pharmacy"), ("shop", "chemist")),
        weak_tags=(),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "dental clinic": CompetitorRule(
        aliases=("dental", "dentist", "orthodont", "smile", "teeth"),
        strong_tags=(("amenity", "dentist"),),
        weak_tags=(),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "tutoring center": CompetitorRule(
        aliases=("tutor", "tutoring", "learning centre", "learning center", "education centre", "education center", "kumon", "sylvan", "mathnasium"),
        strong_tags=(("office", "educational_institution"),),
        weak_tags=(("amenity", "school"),),
        reject_terms=("public school", "catholic school", "high school", "elementary", "college", "university"),
        min_score=58,
    ),
    "daycare center": CompetitorRule(
        aliases=("daycare", "childcare", "child care", "early learning", "nursery", "preschool", "kindergarten", "montessori"),
        strong_tags=(("amenity", "kindergarten"), ("amenity", "childcare")),
        weak_tags=(),
        min_score=38,
        weak_tag_requires_alias=False,
    ),
    "hair salon": CompetitorRule(
        aliases=("hair", "salon", "beauty salon", "hairdresser", "hairstyling", "cuts", "colour", "color"),
        strong_tags=(("shop", "hairdresser"),),
        weak_tags=(("shop", "beauty"),),
        reject_terms=("nail", "spa", "cosmetics", "barber"),
        min_score=45,
    ),
    "nail salon": CompetitorRule(
        aliases=("nail", "nails", "manicure", "pedicure", "spa", "beauty bar"),
        strong_tags=(),
        weak_tags=(("shop", "beauty"), ("shop", "cosmetics")),
        reject_terms=("hair", "barber", "eyebrow", "lash"),
        min_score=55,
    ),
    "barbershop": CompetitorRule(
        aliases=("barber", "barbershop", "barber shop", "men's hair", "mens hair", "cuts"),
        strong_tags=(),
        weak_tags=(("shop", "hairdresser"),),
        reject_terms=("nail", "spa", "beauty", "salon"),
        min_score=55,
    ),
    "laundromat": CompetitorRule(
        aliases=("laundry", "laundromat", "coin laundry", "dry cleaner", "wash", "cleaners"),
        strong_tags=(("shop", "laundry"), ("amenity", "laundry")),
        weak_tags=(),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "clothing boutique": CompetitorRule(
        aliases=("clothing", "clothes", "fashion", "boutique", "apparel", "wear", "outfit", "dress"),
        strong_tags=(("shop", "clothes"),),
        weak_tags=(),
        reject_terms=("thrift", "donation", "laundry", "tailor"),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "pet supply store": CompetitorRule(
        aliases=("pet", "pets", "pet food", "pet supply", "pet supplies", "pet valu", "petsmart"),
        strong_tags=(("shop", "pet"),),
        weak_tags=(),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
    "electronics repair shop": CompetitorRule(
        aliases=("electronics repair", "phone repair", "cell repair", "computer repair", "device repair", "mobile repair", "tech repair", "repair"),
        strong_tags=(("craft", "electronics_repair"),),
        weak_tags=(("shop", "electronics"),),
        reject_terms=("best buy", "the source", "staples", "retail", "appliance"),
        min_score=55,
    ),
    "florist": CompetitorRule(
        aliases=("florist", "flowers", "flower", "floral", "bouquet"),
        strong_tags=(("shop", "florist"),),
        weak_tags=(),
        min_score=35,
        weak_tag_requires_alias=False,
    ),
}

TRANSIT_TAGS: List[Tuple[str, str]] = [
    ("highway", "bus_stop"),
    ("public_transport", "platform"),
    ("railway", "station"),
    ("railway", "tram_stop"),
]

COMMERCIAL_ACTIVITY_TAGS: List[Tuple[str, str]] = [
    ("shop", "mall"),
    ("shop", "department_store"),
    ("amenity", "marketplace"),
    ("amenity", "bank"),
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _clean_text(value: object) -> str:
    text = str(value or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9+]+", " ", text)
    return " ".join(text.split())


def _contains_phrase(text: str, phrase: str) -> bool:
    clean_phrase = _clean_text(phrase)
    if not clean_phrase:
        return False
    return clean_phrase in text


def _subcategory_tokens(business_subcategory: str) -> Tuple[str, ...]:
    tokens = []
    for token in _clean_text(business_subcategory).split():
        if token not in GENERIC_BUSINESS_WORDS and len(token) >= 3:
            tokens.append(token)
    return tuple(tokens)


def _tag_pair_matches(tags: Dict[str, object], pair: Tuple[str, str]) -> bool:
    key, expected = pair
    actual = _clean_text(tags.get(key))
    return actual == _clean_text(expected)


def _all_searchable_text(item: Dict) -> str:
    tags = item.get("tags", {}) or {}
    useful_values = [
        item.get("name"),
        tags.get("name"),
        tags.get("brand"),
        tags.get("operator"),
        tags.get("shop"),
        tags.get("amenity"),
        tags.get("leisure"),
        tags.get("office"),
        tags.get("healthcare"),
        tags.get("craft"),
        tags.get("sport"),
        tags.get("cuisine"),
        tags.get("description"),
        tags.get("alt_name"),
        tags.get("official_name"),
        tags.get("keyword"),
    ]
    return _clean_text(" ".join(str(value or "") for value in useful_values))


def _default_rule_for_subcategory(business_subcategory: str) -> CompetitorRule:
    tags = tuple(get_osm_tags_for_subcategory(business_subcategory))
    tokens = _subcategory_tokens(business_subcategory)
    return CompetitorRule(
        aliases=tokens,
        strong_tags=tags,
        weak_tags=(),
        reject_terms=(),
        min_score=40,
        weak_tag_requires_alias=False,
    )


def _rule_for_subcategory(business_subcategory: str) -> CompetitorRule:
    key = _clean_text(business_subcategory)
    return COMPETITOR_RULES.get(key) or _default_rule_for_subcategory(business_subcategory)


def _competitor_relevance_score(item: Dict, business_subcategory: str) -> Tuple[int, List[str]]:
    rule = _rule_for_subcategory(business_subcategory)
    tags = item.get("tags", {}) or {}
    text = _all_searchable_text(item)
    reasons: List[str] = []
    score = 0

    strong_tag_hit = any(_tag_pair_matches(tags, pair) for pair in rule.strong_tags)
    weak_tag_hit = any(_tag_pair_matches(tags, pair) for pair in rule.weak_tags)
    alias_hits = [alias for alias in rule.aliases if _contains_phrase(text, alias)]
    token_hits = [token for token in _subcategory_tokens(business_subcategory) if _contains_phrase(text, token)]
    reject_hits = [term for term in rule.reject_terms if _contains_phrase(text, term)]

    if strong_tag_hit:
        score += 45
        reasons.append("matched strong OSM business tag")

    if weak_tag_hit:
        score += 22
        reasons.append("matched broad OSM business tag")

    if alias_hits:
        score += min(45, 20 + len(alias_hits) * 8)
        reasons.append(f"matched business terms: {', '.join(alias_hits[:3])}")

    if token_hits:
        score += min(20, len(token_hits) * 6)
        reasons.append(f"matched subcategory tokens: {', '.join(token_hits[:3])}")

    # Cuisine/product/service-specific OSM tags are strong hints when present.
    cuisine = _clean_text(tags.get("cuisine"))
    if cuisine and any(_contains_phrase(cuisine, alias) for alias in rule.aliases):
        score += 30
        reasons.append("matched cuisine/service tag")

    if reject_hits:
        score -= 70
        reasons.append(f"rejected unrelated terms: {', '.join(reject_hits[:3])}")

    if weak_tag_hit and rule.weak_tag_requires_alias and not alias_hits and not token_hits:
        score -= 45
        reasons.append("broad tag without business-specific name/tag evidence")

    # A category-tagged business whose own name/brand carries a defining term for this
    # subcategory IS a competitor. Without this, a single alias hit on a broad tag scored
    # 22 + 28 = 50 against the niche rules' 55 threshold, so "Desi Point" (shop=convenience,
    # name matches "desi") was dropped from an Indian-grocery scan — a false negative
    # anyone can spot on the map. Two independent signals clear the bar; a reject term
    # still wins, because that is the case where the name is misleading.
    if alias_hits and (strong_tag_hit or weak_tag_hit) and not reject_hits:
        score = max(score, rule.min_score)
        reasons.append("name/brand matches this business type and the OSM category fits")

    return score, reasons


def _is_relevant_competitor(item: Dict, business_subcategory: str) -> bool:
    rule = _rule_for_subcategory(business_subcategory)
    score, reasons = _competitor_relevance_score(item, business_subcategory)
    item["relevance_score"] = score
    item["relevance_reasons"] = reasons
    return score >= rule.min_score


def _tag_query(tags: List[Tuple[str, str]], lat: float, lon: float, radius_m: int) -> str:
    clauses = []
    for key, value in tags:
        safe_key = key.replace('"', "")
        safe_value = value.replace('"', "")
        clauses.append(f'node["{safe_key}"="{safe_value}"](around:{radius_m},{lat},{lon});')
        clauses.append(f'way["{safe_key}"="{safe_value}"](around:{radius_m},{lat},{lon});')
        clauses.append(f'relation["{safe_key}"="{safe_value}"](around:{radius_m},{lat},{lon});')
    return "".join(clauses)


def build_overpass_query(tags: List[Tuple[str, str]], lat: float, lon: float, radius_km: float, limit: int = 80) -> str:
    radius_m = int(max(250, min(radius_km * 1000, 25000)))
    body = _tag_query(tags, lat, lon, radius_m)
    return f"""
[out:json][timeout:{OVERPASS_TIMEOUT_SECONDS}];
(
  {body}
);
out center {limit};
""".strip()


def _query_overpass_endpoint(endpoint: str, query: str) -> List[Dict]:
    """POST the query to a single Overpass endpoint and return its elements.

    Raises on failure so the caller can try the next mirror.
    """
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"User-Agent": "ZonalyzeCapstone/1.0 (educational prototype)"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=OVERPASS_HTTP_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("elements", []) or []


def _serve_stale(cached_result: OSMFetchResult) -> OSMFetchResult:
    """Return cached OSM data when the live API is down. It is genuine (older) OSM
    data, so we keep status='live_osm' to preserve downstream relevance filtering
    and evidence, and make the note tell the truth."""
    return OSMFetchResult(
        status="live_osm",
        note=(
            "Live Overpass was unavailable, so Zonalyze is showing the most recent cached "
            "OpenStreetMap results for this area."
        ),
        elements=cached_result.elements,
    )


def _empty_fallback(cache_key: str, now: float, note: str) -> OSMFetchResult:
    result = OSMFetchResult(status="fallback_proxy", note=note, elements=[])
    # Cache the failure only briefly so a recovering network is retried soon.
    _CACHE[cache_key] = (now, result)
    return result


def _fetch_overpass(query: str, cache_key: str) -> OSMFetchResult:
    now = time.time()
    cached = _CACHE.get(cache_key)
    cached_result = cached[1] if cached else None
    if cached:
        cached_at, _res = cached
        # Successful results are cached for the full TTL; failures only briefly,
        # so a transient Overpass outage cannot blank the map for hours.
        ttl = CACHE_TTL_SECONDS if cached_result.status == "live_osm" else FAILURE_CACHE_TTL_SECONDS
        if now - cached_at < ttl:
            return cached_result

    # Circuit open: the network is known-bad right now. Skip the (slow) live attempt
    # and serve cached data instantly if we have any, else return immediately.
    if now < _circuit["open_until"]:
        if cached_result is not None and cached_result.status == "live_osm":
            return _serve_stale(cached_result)
        return _empty_fallback(
            cache_key,
            now,
            "Overpass is being skipped briefly after repeated failures (likely a blocked or throttled "
            "network). No cached results exist yet for this area — retry once Overpass is reachable.",
        )

    endpoints = _overpass_endpoints()
    errors: List[str] = []
    for endpoint in endpoints:
        try:
            elements = _query_overpass_endpoint(endpoint, query)
            result = OSMFetchResult(
                status="live_osm",
                note=(
                    "OpenStreetMap data retrieved through the public Overpass API. "
                    "Competitor results are filtered by Zonalyze relevance scoring before display."
                ),
                elements=elements,
            )
            _CACHE[cache_key] = (now, result)
            _circuit["failures"] = 0
            _circuit["open_until"] = 0.0
            _save_disk_cache()
            return result
        except Exception as exc:  # rate limit / timeout / network — try next mirror
            errors.append(f"{endpoint.split('//')[-1].split('/')[0]}: {type(exc).__name__}")
            logger.warning("Overpass endpoint failed (%s): %s", endpoint, exc)
            continue

    # Every mirror failed. Trip the circuit breaker so we stop hammering a dead
    # network on every subsequent request.
    _circuit["failures"] += 1
    if _circuit["failures"] >= _CIRCUIT_FAIL_THRESHOLD:
        _circuit["open_until"] = now + _CIRCUIT_COOLDOWN_SECONDS

    # Prefer stale cached OSM data over a blank map — this is the whole point of
    # the disk cache: once fetched, competitors keep showing when Overpass is down.
    if cached_result is not None and cached_result.status == "live_osm":
        return _serve_stale(cached_result)

    return _empty_fallback(
        cache_key,
        now,
        (
            "Live OpenStreetMap query failed on all endpoints, and no cached results exist yet for "
            f"this area. Tried {len(endpoints)} endpoint(s): {'; '.join(errors)}. This is usually a "
            "temporary Overpass rate-limit/outage or a network that blocks it — retry shortly, or run "
            "the prefetch script on a working network."
        ),
    )


def _fetch_pois_or_overpass(
    query_tags: List[Tuple[str, str]],
    center_lat: float,
    center_lon: float,
    radius_km: float,
    limit: int,
    query: str,
    cache_key: str,
    store_only: bool = False,
    precise_tags: List[Tuple[str, str]] | None = None,
    keywords: List[str] | None = None,
) -> OSMFetchResult:
    """Local PostGIS POI store first (owned, no rate limits); Overpass only if the
    store isn't available yet. Reuses status='live_osm' so downstream relevance
    filtering/evidence is unchanged (the note states the real source).

    store_only=True skips the Overpass fallback entirely — for frequent callers
    (the dashboard) that must never wait on a live network call."""
    elements = poi_query_service.fetch_pois_from_db(
        query_tags, center_lat, center_lon, radius_km, limit,
        precise_tags=precise_tags, keywords=keywords,
    )
    if elements is not None:  # store answered (even 0 rows = a real "none nearby")
        return OSMFetchResult(
            status="live_osm",
            note="OpenStreetMap POIs served from Zonalyze's local PostGIS mirror (no live Overpass call).",
            elements=elements,
        )
    if store_only:
        return OSMFetchResult(
            status="fallback_proxy",
            note="Local POI store not imported yet; skipped live Overpass for this call.",
            elements=[],
        )
    return _fetch_overpass(query, cache_key)


def _normalize_element(element: Dict, center_lat: float, center_lon: float, category: str) -> Dict | None:
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lon = element.get("lon") or element.get("center", {}).get("lon")
    if lat is None or lon is None:
        return None

    tags = element.get("tags", {}) or {}
    name = tags.get("name") or tags.get("brand") or category
    address_parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
    ]
    address = " ".join([part for part in address_parts if part]) or None
    address_source = "openstreetmap_tags" if address else None
    distance_km = haversine_km(center_lat, center_lon, float(lat), float(lon))
    return {
        "osm_id": str(element.get("id")),
        "osm_type": str(element.get("type")),
        "name": name,
        "latitude": float(lat),
        "longitude": float(lon),
        "category": category,
        "address": address,
        "address_source": address_source,
        "distance_km": round(distance_km, 3),
        "tags": tags,
    }


def _dedupe_tags(tags: Iterable[Tuple[str, str]]) -> List[Tuple[str, str]]:
    seen = set()
    unique: List[Tuple[str, str]] = []
    for key, value in tags:
        pair = (str(key), str(value))
        if pair not in seen:
            seen.add(pair)
            unique.append(pair)
    return unique


def fetch_osm_competitors(
    business_subcategory: str,
    center_lat: float,
    center_lon: float,
    radius_km: float,
    limit: int = 60,
    store_only: bool = False,
) -> OSMFetchResult:
    catalog_tags = get_osm_tags_for_subcategory(business_subcategory)
    rule = _rule_for_subcategory(business_subcategory)
    query_tags = _dedupe_tags([*catalog_tags, *rule.strong_tags, *rule.weak_tags])
    # The store row cap used to bind long before the radius did (weak tags like
    # amenity=restaurant fill it within a few km downtown), so the competitor count
    # stopped moving when the user widened the reach. Prefiltering in SQL by the
    # subcategory's own aliases keeps the cap far out of reach instead of raising it.
    #
    # search_limit (candidates considered) and `limit` (results actually returned)
    # are deliberately different: widening the search fixed the radius bug, but
    # returning all of it to every caller flooded the map with hundreds of un-
    # clustered pins that were never meant to render (only a count needs the full
    # number — see dashboard_service, which asks for a high `limit` on purpose).
    keywords = [w for w in dict.fromkeys([*rule.aliases, *_subcategory_tokens(business_subcategory)]) if w]
    search_limit = max(limit, 2000)

    query = build_overpass_query(query_tags, center_lat, center_lon, radius_km, limit=max(limit, 80))
    cache_key = f"competitors:v4:{business_subcategory}:{center_lat:.4f}:{center_lon:.4f}:{radius_km}:{limit}"
    result = _fetch_pois_or_overpass(
        query_tags, center_lat, center_lon, radius_km, search_limit, query, cache_key,
        store_only=store_only, precise_tags=rule.strong_tags, keywords=keywords,
    )

    normalized: List[Dict] = []
    seen = set()
    raw_count = len(result.elements)

    for element in result.elements:
        item = _normalize_element(element, center_lat, center_lon, business_subcategory)
        if not item:
            continue
        key = (item["osm_type"], item["osm_id"])
        if key in seen:
            continue
        seen.add(key)

        if result.status == "live_osm" and not _is_relevant_competitor(item, business_subcategory):
            continue

        normalized.append(item)

    normalized.sort(key=lambda row: (-int(row.get("relevance_score", 0)), row["distance_km"]))

    if result.status == "live_osm":
        kept = len(normalized)
        note = (
            f"Scanned {raw_count} mapped businesses within {radius_km:g} km whose OpenStreetMap "
            f"category could plausibly compete with '{business_subcategory}', and kept {kept} "
            f"after relevance scoring (name, brand, cuisine and category tags)."
        )
        # A count equal to the cap is a floor, not a total. Saying so beats quietly
        # presenting a truncated number as if it were the whole market.
        if kept > limit:
            note += (
                f" More than {limit} matched, so the reported count is capped at {limit} "
                "and should be read as 'at least'."
            )
    else:
        note = result.note

    return OSMFetchResult(status=result.status, note=note, elements=normalized[:limit])


def fetch_osm_transit(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    limit: int = 40,
) -> OSMFetchResult:
    query = build_overpass_query(TRANSIT_TAGS, center_lat, center_lon, radius_km, limit=limit)
    cache_key = f"transit:{center_lat:.4f}:{center_lon:.4f}:{radius_km}:{limit}"
    result = _fetch_pois_or_overpass(TRANSIT_TAGS, center_lat, center_lon, radius_km, limit, query, cache_key)
    normalized: List[Dict] = []
    seen = set()
    for element in result.elements:
        item = _normalize_element(element, center_lat, center_lon, "Transit / Mobility")
        if not item:
            continue
        key = (item["osm_type"], item["osm_id"])
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    normalized.sort(key=lambda row: row["distance_km"])
    return OSMFetchResult(status=result.status, note=result.note, elements=normalized[:limit])


def fetch_osm_commercial_activity(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    limit: int = 30,
) -> OSMFetchResult:
    query = build_overpass_query(COMMERCIAL_ACTIVITY_TAGS, center_lat, center_lon, radius_km, limit=limit)
    cache_key = f"commercial:{center_lat:.4f}:{center_lon:.4f}:{radius_km}:{limit}"
    result = _fetch_pois_or_overpass(COMMERCIAL_ACTIVITY_TAGS, center_lat, center_lon, radius_km, limit, query, cache_key)
    normalized: List[Dict] = []
    seen = set()
    for element in result.elements:
        item = _normalize_element(element, center_lat, center_lon, "Commercial activity")
        if not item:
            continue
        key = (item["osm_type"], item["osm_id"])
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    normalized.sort(key=lambda row: row["distance_km"])
    return OSMFetchResult(status=result.status, note=result.note, elements=normalized[:limit])


def _resolved_tag_to_tuple(tag: object) -> Tuple[str, str, str, float]:
    """Convert a resolved AI tag object/dict into a generic Overpass tag tuple.

    This performs no business-specific mapping. It only reads the already resolved
    OSM key/value/role/confidence returned by the dynamic business resolver.
    """
    if isinstance(tag, dict):
        key = str(tag.get("key") or "").strip()
        value = str(tag.get("value") or "").strip()
        role = str(tag.get("tag_role") or "primary").strip().lower()
        confidence_raw = tag.get("confidence", 0.5)
    else:
        key = str(getattr(tag, "key", "") or "").strip()
        value = str(getattr(tag, "value", "") or "").strip()
        role = str(getattr(tag, "tag_role", "primary") or "primary").strip().lower()
        confidence_raw = getattr(tag, "confidence", 0.5)

    try:
        confidence = float(confidence_raw)
    except Exception:
        confidence = 0.5

    return key, value, role, max(0.0, min(1.0, confidence))


def _select_query_tags_from_resolved_tags(resolved_tags: Iterable[object]) -> List[Tuple[str, str]]:
    """Select tags for competitor/POI lookup from AI-resolved OSM tags.

    The selection is role-based and generic. Brand/name/operator tags are useful
    as metadata, but using only brand filters can hide ordinary competitors. For
    market evidence, primary/secondary/category-style tags are preferred. If the
    AI only returns brand/name/operator tags, the function uses those tags rather
    than inventing category tags.
    """
    parsed = []
    for tag in resolved_tags or []:
        key, value, role, confidence = _resolved_tag_to_tuple(tag)
        if not key or not value:
            continue
        parsed.append((key, value, role, confidence))

    category_like_roles = {"primary", "secondary", "attribute", "specialty", "other"}
    category_tags = [
        (key, value)
        for key, value, role, confidence in parsed
        if role in category_like_roles and key not in {"brand", "name", "operator"}
    ]

    if category_tags:
        return _dedupe_tags(category_tags)

    # No category-like tags were available. Use the resolved tags as-is instead
    # of guessing replacements. This keeps the no-hardcoded-business-mapping rule.
    return _dedupe_tags([(key, value) for key, value, role, confidence in parsed])


def fetch_osm_pois_by_resolved_tags(
    *,
    resolved_tags: Iterable[object],
    business_label: str,
    center_lat: float,
    center_lon: float,
    radius_km: float,
    limit: int = 60,
) -> OSMFetchResult:
    """Fetch OSM POIs using AI-resolved tags instead of hardcoded category rules.

    This is the Step 27B dynamic path. It intentionally does not use
    COMPETITOR_RULES, business catalog mappings, keyword rules, or brand lists.
    It trusts only validated tags already returned by the business resolver.
    """
    query_tags = _select_query_tags_from_resolved_tags(resolved_tags)

    if not query_tags:
        return OSMFetchResult(
            status="business_resolution_needs_review",
            note=(
                "No validated dynamic OSM tags were available, so Zonalyze did not run "
                "a competitor/POI query for this free-text business idea."
            ),
            elements=[],
        )

    query = build_overpass_query(query_tags, center_lat, center_lon, radius_km, limit=max(limit, 80))
    tag_key = ";".join([f"{key}={value}" for key, value in query_tags])
    cache_key = f"dynamic-business-tags:v1:{tag_key}:{center_lat:.4f}:{center_lon:.4f}:{radius_km}:{limit}"
    result = _fetch_overpass(query, cache_key)

    normalized: List[Dict] = []
    seen = set()
    raw_count = len(result.elements)

    for element in result.elements:
        item = _normalize_element(element, center_lat, center_lon, business_label or "Resolved business POI")
        if not item:
            continue
        key = (item["osm_type"], item["osm_id"])
        if key in seen:
            continue
        seen.add(key)
        item["relevance_score"] = None
        item["relevance_reasons"] = ["Matched AI-resolved validated OSM tag query."]
        normalized.append(item)

    normalized.sort(key=lambda row: row["distance_km"])

    if result.status == "live_osm":
        note = (
            f"OpenStreetMap returned {raw_count} raw POIs using AI-resolved OSM tags "
            f"for '{business_label}'. Zonalyze displayed {len(normalized)} nearby POIs "
            "without hardcoded business-category relevance rules."
        )
    else:
        note = result.note

    return OSMFetchResult(status=result.status, note=note, elements=normalized[:limit])
