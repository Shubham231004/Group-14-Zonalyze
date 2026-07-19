import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Zonalyze")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", 8000))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "zonalyze_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sss@1008")

ENCODED_DB_PASSWORD = quote_plus(DB_PASSWORD)

DATABASE_URL = (
    f"postgresql://{DB_USER}:{ENCODED_DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
# Mapbox token is optional. It is only used as a fallback to reverse-geocode
# competitor marker addresses when OpenStreetMap does not provide addr:* tags.
# Keep the real token in backend/.env and do not commit it to GitHub.
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "")
