FROM python:3.12-slim

WORKDIR /app

# psycopg2-binary needs libpq at runtime; libpq-dev covers build too.
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Model .pkl files are not in the image (see DEPLOYMENT.md) — fetched at
# container startup from MODELS_BASE_URL, then cached in the mounted/ephemeral
# filesystem for the life of the instance.
CMD python -m app.scripts.fetch_models; \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
