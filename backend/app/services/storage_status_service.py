from __future__ import annotations

from app.core.mongo import ping_mongodb
from app.schemas.storage_status import MongoStatusResponse


def get_mongo_status() -> MongoStatusResponse:
    return MongoStatusResponse(**ping_mongodb())
