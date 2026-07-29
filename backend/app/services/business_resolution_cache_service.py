from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.mongo import get_mongo_collection, is_mongo_cache_enabled
from app.schemas.business_resolver import BusinessResolveResponse


CACHE_COLLECTION_NAME = os.getenv("BUSINESS_RESOLUTION_CACHE_COLLECTION", "business_resolution_cache")
CACHE_TTL_HOURS = float(os.getenv("BUSINESS_RESOLUTION_CACHE_TTL_HOURS", "168"))
CACHE_SCHEMA_VERSION = "business-resolution-cache-v1"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _cache_key(*, business_query: str, model: Optional[str] = None) -> str:
    normalized_query = " ".join(str(business_query or "").strip().lower().split())
    normalized_model = " ".join(str(model or "default").strip().lower().split())
    raw_key = f"{CACHE_SCHEMA_VERSION}|{normalized_model}|{normalized_query}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _collection():
    """Return the MongoDB cache collection or None.

    This function is intentionally fail-open. MongoDB is a performance cache,
    not required infrastructure. DNS, Atlas, or network failure must not break
    /business/resolve.
    """
    if not is_mongo_cache_enabled():
        return None

    try:
        return get_mongo_collection(CACHE_COLLECTION_NAME)
    except Exception:
        return None


def get_cached_business_resolution(*, business_query: str, model: Optional[str] = None) -> Optional[BusinessResolveResponse]:
    """Return cached business resolution if available.

    This function must never crash /business/resolve. If MongoDB Atlas DNS/network
    fails on a teammate laptop, return None and let the normal Ollama/Taginfo flow run.
    """
    try:
        collection = _collection()
        if collection is None:
            return None

        cache_key = _cache_key(business_query=business_query, model=model)
        document = collection.find_one({"_id": cache_key})
        if not document:
            return None

        expires_at = document.get("expires_at")
        if isinstance(expires_at, datetime) and expires_at < _now_utc():
            try:
                collection.delete_one({"_id": cache_key})
            except Exception:
                pass
            return None

        payload = document.get("response")
        if not isinstance(payload, dict):
            return None

        response = BusinessResolveResponse(**payload)
        warnings = list(response.warnings or [])
        cache_note = "Returned from MongoDB business-resolution cache."
        if cache_note not in warnings:
            warnings.insert(0, cache_note)
        response.warnings = warnings
        return response
    except Exception:
        # Cache read failure must never break business resolution.
        return None


def save_business_resolution_cache(
    *,
    business_query: str,
    model: Optional[str] = None,
    response: BusinessResolveResponse,
) -> bool:
    """Save successful business resolution to MongoDB cache.

    Returns False on any MongoDB/network/serialization failure. Never raises.
    """
    try:
        if response.status != "resolved":
            return False

        collection = _collection()
        if collection is None:
            return False

        cache_key = _cache_key(business_query=business_query, model=model)
        now = _now_utc()
        expires_at = now + timedelta(hours=CACHE_TTL_HOURS)

        if hasattr(response, "model_dump"):
            response_payload = response.model_dump(mode="json")
        else:
            response_payload = response.dict()

        collection.update_one(
            {"_id": cache_key},
            {
                "$set": {
                    "business_query": business_query,
                    "model": model,
                    "response": response_payload,
                    "updated_at": now,
                    "expires_at": expires_at,
                    "schema_version": CACHE_SCHEMA_VERSION,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return True
    except Exception:
        # Cache write failure must never break the API.
        return False


def get_business_resolution_cache_status() -> dict[str, Any]:
    try:
        collection = _collection()
        if collection is None:
            return {
                "status": "disabled_or_unreachable",
                "collection_name": CACHE_COLLECTION_NAME,
                "ttl_hours": CACHE_TTL_HOURS,
                "document_count": None,
                "message": (
                    "Business-resolution cache is disabled or unreachable. "
                    "The resolver will continue without MongoDB cache."
                ),
            }
        return {
            "status": "available",
            "collection_name": CACHE_COLLECTION_NAME,
            "ttl_hours": CACHE_TTL_HOURS,
            "document_count": collection.estimated_document_count(),
        }
    except Exception as exc:
        return {
            "status": "unreachable",
            "collection_name": CACHE_COLLECTION_NAME,
            "ttl_hours": CACHE_TTL_HOURS,
            "document_count": None,
            "message": f"Cache status check failed without crashing the app: {type(exc).__name__}: {exc}",
        }
