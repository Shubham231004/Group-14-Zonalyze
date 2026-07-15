# Zonalyze Backend

FastAPI service for business feasibility scenarios: ML predictions (revenue, risk,
feasibility), evidence layers (competition, lease, demand), geospatial/OSM market
context, and local-AI helpers.

## Prerequisites

- Python 3.13 (a virtual environment is expected)
- PostgreSQL (census + scenario history)
- MongoDB (caches: operating profile, business resolution, market map)
- [Ollama](https://ollama.com/) running locally with a model pulled, for the AI
  features: `ollama pull llama3.2:3b`

Copy `.env` and fill in DB, Mongo, Mapbox, and Ollama settings (see the existing
`.env` keys). Do **not** commit real secrets.

## Install

```bash
cd backend
python -m venv ../Zonalyze          # or your preferred venv location
../Zonalyze/Scripts/activate         # Windows; use bin/activate on macOS/Linux
pip install -r requirements.txt
```

## Train the ML models (required before first run)

The trained model artifacts (`app/ml/models/*.pkl`) and the generated training
dataset are **intentionally gitignored** (they are large and machine-generated),
so a fresh clone will not have them. Build them locally:

```bash
cd backend
python -m app.ml.train_models --rows 50000 --force-regenerate
```

This regenerates `app/data/generated/zonalyze_training_dataset_v2.csv` and writes
`risk_classifier.pkl`, `revenue_regressor.pkl`, `feasibility_regressor.pkl`,
`feature_columns.json`, and `model_metadata.json` into `app/ml/models/`.

Training and live inference share one feature pipeline
(`app/ml/feature_pipeline.py`), so predictions match the data the models were
trained on. If you change that pipeline, **retrain** — otherwise `/ml/model-status`
and `/ml/feature-alignment` will flag the drift.

If the model files are missing, prediction endpoints return HTTP 503 with a
`models_unavailable` message and the retrain command (they no longer crash).

## Run

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check: `GET http://127.0.0.1:8000/health`.
Model status: `GET http://127.0.0.1:8000/ml/model-status`.
