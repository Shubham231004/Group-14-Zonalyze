from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.mongo import get_mongo_database, is_mongo_configured


COLLECTION_NAME = os.getenv("MARKET_MAP_CACHE_COLLECTION", "market_map_cache")
CACHE_TTL_HOURS = int(os.getenv("MARKET_MAP_CACHE_TTL_HOURS", "24"))
CACHE_SCHEMA_VERSION = "market_map_cache_v1"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def build_market_map_cache_key(
    *,
    municipality_name: str,
    radius_km: float,
    business_subcategory: Optional[str] = None,
    business_query: Optional[str] = None,
    resolved_osm_tags: Optional[list[dict[str, Any]]] = None,
) -> str:
    """
    Build a stable cache key for map evidence.

    The key is based on the user scenario plus resolved OSM tags when present.
    It does not store secrets and does not assume hardcoded business categories.
    """
    normalized_tags = []
    for tag in resolved_osm_tags or []:
        if not isinstance(tag, dict):
            continue
        normalized_tags.append(
            {
                "key": _normalize_text(tag.get("key")),
                "value": _normalize_text(tag.get("value")),
                "role": _normalize_text(tag.get("tag_role")),
            }
        )
    normalized_tags = sorted(normalized_tags, key=lambda item: (item["key"], item["value"], item["role"]))

    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "municipality_name": _normalize_text(municipality_name),
        "radius_km": round(float(radius_km or 0), 3),
        "business_subcategory": _normalize_text(business_subcategory),
        "business_query": _normalize_text(business_query),
        "resolved_osm_tags": normalized_tags,
    }

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{CACHE_SCHEMA_VERSION}:{digest}"


def _collection():
    if not is_mongo_configured():
        return None
    try:
        db = get_mongo_database()
        return db[COLLECTION_NAME]
    except Exception:
        return None


def _to_plain_json(value: Any) -> Any:
    """
    Convert Pydantic models, datetimes, and nested objects into Mongo-safe JSON.
    """
    if hasattr(value, "model_dump"):
        return _to_plain_json(value.model_dump())
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _to_plain_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain_json(item) for item in value]
    return value


def get_cached_market_map(cache_key: str) -> Optional[dict[str, Any]]:
    collection = _collection()
    if collection is None:
        return None

    try:
        document = collection.find_one({"cache_key": cache_key})
        if not document:
            return None

        expires_at = document.get("expires_at")
        if isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= _utc_now():
                collection.delete_one({"cache_key": cache_key})
                return None

        response_payload = document.get("response_payload")
        if not isinstance(response_payload, dict):
            return None

        response_payload["cache_status"] = "hit"
        response_payload["cache_source"] = "mongodb_market_map_cache"
        response_payload["cached_at"] = document.get("cached_at").isoformat() if isinstance(document.get("cached_at"), datetime) else document.get("cached_at")
        return response_payload
    except Exception:
        return None


def save_market_map_cache(
    *,
    cache_key: str,
    request_summary: dict[str, Any],
    response_payload: Any,
) -> None:
    collection = _collection()
    if collection is None:
        return

    try:
        now = _utc_now()
        plain_payload = _to_plain_json(response_payload)
        if not isinstance(plain_payload, dict):
            return

        # Do not persist transient cache metadata from a previous response.
        plain_payload.pop("cache_status", None)
        plain_payload.pop("cache_source", None)
        plain_payload.pop("cached_at", None)

        document = {
            "cache_key": cache_key,
            "schema_version": CACHE_SCHEMA_VERSION,
            "request_summary": _to_plain_json(request_summary),
            "response_payload": plain_payload,
            "cached_at": now,
            "expires_at": now + timedelta(hours=CACHE_TTL_HOURS),
        }

        collection.update_one(
            {"cache_key": cache_key},
            {"$set": document},
            upsert=True,
        )
    except Exception:
        # Cache failures must never break geospatial analysis.
        return


def get_market_map_cache_status() -> dict[str, Any]:
    collection = _collection()
    if collection is None:
        return {
            "status": "disabled",
            "collection_name": COLLECTION_NAME,
            "cache_ttl_hours": CACHE_TTL_HOURS,
            "message": "MongoDB is not configured or unavailable.",
        }

    try:
        count = collection.count_documents({})
        return {
            "status": "enabled",
            "collection_name": COLLECTION_NAME,
            "cache_ttl_hours": CACHE_TTL_HOURS,
            "document_count": count,
            "message": "MongoDB market-map cache is available.",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "collection_name": COLLECTION_NAME,
            "cache_ttl_hours": CACHE_TTL_HOURS,
            "message": f"MongoDB market-map cache check failed: {exc}",
        }
