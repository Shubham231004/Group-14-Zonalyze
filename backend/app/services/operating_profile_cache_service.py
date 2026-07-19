from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.mongo import get_mongo_collection
from app.schemas.operating_profile import OperatingProfileResponse


CACHE_COLLECTION_NAME = os.getenv("OPERATING_PROFILE_CACHE_COLLECTION", "operating_profile_cache")
CACHE_TTL_HOURS = float(os.getenv("OPERATING_PROFILE_CACHE_TTL_HOURS", "72"))
CACHE_SCHEMA_VERSION = "operating-profile-cache-v1"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _cache_key(*, municipality_name: str, radius_km: float, business_query: Optional[str], business_subcategory: Optional[str], model: Optional[str]) -> str:
    raw = "|".join([
        CACHE_SCHEMA_VERSION,
        " ".join(str(municipality_name or "").lower().split()),
        f"{float(radius_km or 0):.3f}",
        " ".join(str(business_query or "").lower().split()),
        " ".join(str(business_subcategory or "").lower().split()),
        " ".join(str(model or "default").lower().split()),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _collection():
    try:
        return get_mongo_collection(CACHE_COLLECTION_NAME)
    except Exception:
        return None


def get_cached_operating_profile(
    *,
    municipality_name: str,
    radius_km: float,
    business_query: Optional[str],
    business_subcategory: Optional[str],
    model: Optional[str],
) -> Optional[OperatingProfileResponse]:
    try:
        collection = _collection()
        if collection is None:
            return None

        key = _cache_key(
            municipality_name=municipality_name,
            radius_km=radius_km,
            business_query=business_query,
            business_subcategory=business_subcategory,
            model=model,
        )
        document = collection.find_one({"_id": key})
        if not document:
            return None

        expires_at = document.get("expires_at")
        # MongoDB returns naive datetimes (UTC) unless the client is tz_aware.
        # Treat a naive value as UTC so comparing it to a tz-aware "now" does not
        # raise TypeError (which the outer except would swallow, silently forcing
        # every lookup to miss even when a valid cache document exists).
        if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if isinstance(expires_at, datetime) and expires_at < _now_utc():
            try:
                collection.delete_one({"_id": key})
            except Exception:
                pass
            return None

        payload = document.get("response")
        if not isinstance(payload, dict):
            return None

        response = OperatingProfileResponse(**payload)
        response.cache_status = "hit"
        return response
    except Exception:
        return None


def save_operating_profile_cache(
    *,
    municipality_name: str,
    radius_km: float,
    business_query: Optional[str],
    business_subcategory: Optional[str],
    model: Optional[str],
    response: OperatingProfileResponse,
) -> bool:
    try:
        # Cache any successful generation. A success can carry several status
        # labels (estimated, evidence_supported, limited_estimate, ...), so use a
        # denylist of failure states rather than a narrow allowlist that would
        # reject valid outputs and force a re-run. Only skip explicit failures and
        # responses with no usable sections.
        if response.status in {"ai_unavailable", "error"} or not response.sections:
            return False

        collection = _collection()
        if collection is None:
            return False

        key = _cache_key(
            municipality_name=municipality_name,
            radius_km=radius_km,
            business_query=business_query,
            business_subcategory=business_subcategory,
            model=model,
        )
        now = _now_utc()
        expires_at = now + timedelta(hours=CACHE_TTL_HOURS)
        payload = response.model_dump(mode="json") if hasattr(response, "model_dump") else response.dict()
        payload["cache_status"] = "miss_saved"

        collection.update_one(
            {"_id": key},
            {
                "$set": {
                    "municipality_name": municipality_name,
                    "radius_km": radius_km,
                    "business_query": business_query,
                    "business_subcategory": business_subcategory,
                    "model": model,
                    "response": payload,
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
        return False
