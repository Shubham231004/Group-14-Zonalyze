from __future__ import annotations

from pydantic import BaseModel


class MongoStatusResponse(BaseModel):
    enabled: bool
    status: str
    database_name: str
    message: str
