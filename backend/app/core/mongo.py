from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
except Exception:  # pymongo not installed yet
    MongoClient = None  # type: ignore
    Collection = Any  # type: ignore
    Database = Any  # type: ignore


# MongoDB is an optional cloud cache layer for Zonalyze.
# If Atlas/DNS/network is unavailable, the app must continue working without cache.


def _env_bool(name: str, default: str = "true") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _mongo_uri() -> str:
    # Strip spaces and quotes because .env values sometimes get copied as:
    # MONGODB_URI="mongodb+srv://..."
    return (os.getenv("MONGODB_URI") or "").strip().strip('"').strip("'")


def _db_name() -> str:
    return (os.getenv("MONGODB_DB_NAME") or "zonalyze").strip() or "zonalyze"


def is_mongo_cache_enabled() -> bool:
    """Feature flag for the optional MongoDB cache layer.

    Set MONGODB_CACHE_ENABLED=false in .env to force the app to skip MongoDB
    while keeping the URI present for later testing.
    """
    return _env_bool("MONGODB_CACHE_ENABLED", "true")


def is_mongo_configured() -> bool:
    return is_mongo_cache_enabled() and bool(_mongo_uri()) and MongoClient is not None


def _timeout_ms(env_name: str, default: str) -> int:
    try:
        value = int(os.getenv(env_name, default))
        return max(500, min(value, 15000))
    except Exception:
        return int(default)


def _configure_srv_dns_resolver(uri: str) -> None:
    """Make `mongodb+srv://` URIs resolvable on restricted (college/VPN) networks.

    Atlas SRV URIs require a DNS SRV/TXT lookup. Some campus/corporate DNS
    servers silently drop or time out on SRV queries, which makes every cache
    read/write raise and the cache silently no-op (cache_status stays
    "miss_not_saved"). Atlas SRV records are public, so we point dnspython at a
    public resolver (Google/Cloudflare by default) with the system nameservers
    kept as a fallback.

    Controlled by MONGODB_DNS_RESOLVERS (comma-separated IPs). Set it to an empty
    string to disable and use only the system resolver. This never raises.
    """
    if not uri.startswith("mongodb+srv://"):
        return

    resolvers_raw = os.getenv("MONGODB_DNS_RESOLVERS", "8.8.8.8,1.1.1.1")
    public_nameservers = [ip.strip() for ip in resolvers_raw.split(",") if ip.strip()]
    if not public_nameservers:
        return

    try:
        import dns.resolver  # provided by dnspython, a pymongo[srv] dependency

        try:
            system_nameservers = list(dns.resolver.Resolver(configure=True).nameservers)
        except Exception:
            system_nameservers = []

        # Public resolvers first so SRV lookups succeed quickly, then fall back to
        # system DNS for anything the public resolvers cannot answer.
        ordered = public_nameservers + [ns for ns in system_nameservers if ns not in public_nameservers]

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ordered
        resolver.timeout = _timeout_ms("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "2500") / 1000.0
        resolver.lifetime = resolver.timeout * max(1, len(ordered))
        dns.resolver.default_resolver = resolver
    except Exception:
        # dnspython missing or misconfigured: leave the system resolver in place.
        pass


@lru_cache(maxsize=1)
def get_mongo_client() -> Optional[MongoClient]:  # type: ignore[type-arg]
    """Return a MongoDB client, or None if MongoDB cannot be initialized.

    Important:
    - mongodb+srv:// URIs require DNS SRV lookup.
    - On college/VPN/restricted networks, that lookup can timeout.
    - MongoDB is only a cache for Zonalyze, so this function fails open.
    """
    if not is_mongo_configured():
        return None

    uri = _mongo_uri()
    _configure_srv_dns_resolver(uri)
    try:
        return MongoClient(  # type: ignore[operator]
            uri,
            serverSelectionTimeoutMS=_timeout_ms("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "2500"),
            connectTimeoutMS=_timeout_ms("MONGODB_CONNECT_TIMEOUT_MS", "2500"),
            socketTimeoutMS=_timeout_ms("MONGODB_SOCKET_TIMEOUT_MS", "5000"),
            connect=False,
            uuidRepresentation="standard",
            appname="ZonalyzeCapstone",
        )
    except Exception as exc:
        # Invalid URI, DNS SRV timeout, missing dnspython, blocked network, etc.
        # Fail open (cache is optional) but log so the failure is not silent.
        logger.warning("MongoDB client init failed, cache disabled: %s: %s", type(exc).__name__, exc)
        return None


def clear_mongo_client_cache() -> None:
    """Useful during local development after changing .env without restarting Python."""
    try:
        get_mongo_client.cache_clear()
    except Exception:
        pass


def get_mongo_database() -> Optional[Database]:  # type: ignore[type-arg]
    client = get_mongo_client()
    if client is None:
        return None
    try:
        return client[_db_name()]
    except Exception:
        return None


def get_mongo_collection(collection_name: str) -> Optional[Collection]:  # type: ignore[type-arg]
    if not collection_name:
        return None

    database = get_mongo_database()
    if database is None:
        return None

    try:
        return database[collection_name]
    except Exception:
        return None


def ping_mongodb() -> dict[str, Any]:
    """Health check used by /storage/mongo-status.

    This never raises. MongoDB is optional, so failures are reported as JSON.
    """
    if MongoClient is None:
        return {
            "status": "disabled",
            "enabled": False,
            "database_name": _db_name(),
            "cache_enabled": False,
            "message": "pymongo is not installed in this backend environment.",
        }

    if not is_mongo_cache_enabled():
        return {
            "status": "disabled",
            "enabled": False,
            "database_name": _db_name(),
            "cache_enabled": False,
            "message": "MongoDB cache is disabled by MONGODB_CACHE_ENABLED=false.",
        }

    if not _mongo_uri():
        return {
            "status": "disabled",
            "enabled": False,
            "database_name": _db_name(),
            "cache_enabled": False,
            "message": "MONGODB_URI is not configured.",
        }

    try:
        client = get_mongo_client()
        if client is None:
            return {
                "status": "unreachable",
                "enabled": False,
                "database_name": _db_name(),
                "cache_enabled": False,
                "message": (
                    "MongoDB client could not be initialized. Check URI format, DNS, VPN/college network, "
                    "Atlas IP allowlist, or temporarily set MONGODB_CACHE_ENABLED=false."
                ),
            }

        client.admin.command("ping")
        return {
            "status": "connected",
            "enabled": True,
            "database_name": _db_name(),
            "cache_enabled": True,
            "message": "MongoDB connection is healthy.",
        }
    except Exception as exc:
        return {
            "status": "unreachable",
            "enabled": False,
            "database_name": _db_name(),
            "cache_enabled": False,
            "message": f"MongoDB connection failed without crashing the app: {type(exc).__name__}: {exc}",
        }
