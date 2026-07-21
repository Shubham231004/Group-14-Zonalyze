import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Zonalyze")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", 8000))

# When true, SQLAlchemy echoes every SQL statement (and its bound parameter
# values) to the console. Kept OFF by default so real data is never written to
# logs during normal operation. Set DEBUG=true in .env for local debugging.
DEBUG = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "zonalyze_db")
# Prefer a least-privilege application role over the postgres superuser.
DB_USER = os.getenv("DB_USER", "zonalyze_app")

# No hardcoded fallback: the database password must come from the environment.
# The app refuses to start without it, so a real secret can never be shipped in
# source again.
DB_PASSWORD = os.getenv("DB_PASSWORD")
if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is not set. Add it to backend/.env (see backend/.env.example). "
        "The application no longer ships a default database password."
    )

ENCODED_DB_PASSWORD = quote_plus(DB_PASSWORD)

DATABASE_URL = (
    f"postgresql://{DB_USER}:{ENCODED_DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
# Mapbox token is optional. It is only used as a fallback to reverse-geocode
# competitor marker addresses when OpenStreetMap does not provide addr:* tags.
# Keep the real token in backend/.env and do not commit it to GitHub.
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "")

# --- Authentication (Clerk) ---
# Auth is DISABLED unless CLERK_ISSUER is set, so the app runs exactly as before
# until you deliberately opt in by configuring Clerk. When only the issuer is
# provided, the JWKS URL is derived from it.
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "").strip().rstrip("/")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "").strip() or (
    f"{CLERK_ISSUER}/.well-known/jwks.json" if CLERK_ISSUER else ""
)
AUTH_ENABLED = bool(CLERK_ISSUER and CLERK_JWKS_URL)
