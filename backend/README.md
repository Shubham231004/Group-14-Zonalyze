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

## Improving AI response quality (Ollama)

The operating profile, scenario chat, and business resolver use a local Ollama
model. Two things make the biggest difference:

**1. Use a stronger model.** `llama3.2:3b` is small and unreliable at structured
business reasoning. A 7B instruct model is dramatically better at JSON and
instruction-following. Recommended (pull one, then point `OLLAMA_MODEL` at it):

```bash
ollama pull qwen2.5:7b-instruct     # best quality/size balance (recommended)
# or, if RAM-constrained:
ollama pull qwen2.5:3b-instruct     # much better than llama3.2:3b at similar size
```

```
OLLAMA_MODEL=qwen2.5:7b-instruct
```

**2. Structured outputs are enabled.** The JSON endpoints (operating profile,
business resolver) send a JSON **schema** to Ollama, which forces valid,
correctly-typed output (e.g. every operating-profile section must have numeric
low/median/high). This requires **Ollama ≥ 0.5** (`ollama --version`; upgrade if
older). If your Ollama is older and rejects schema output, disable it with
`OLLAMA_JSON_SCHEMA=0` (it falls back to plain JSON mode).

Tuning knobs (all optional, sensible defaults):

```
OLLAMA_MODEL=qwen2.5:7b-instruct   # the model to use
OLLAMA_JSON_SCHEMA=1               # 1=schema-constrained JSON (default), 0=plain json
OLLAMA_NUM_CTX=8192                # chat context window
OLLAMA_JSON_NUM_CTX=8192           # JSON context window
OLLAMA_NUM_PREDICT=700             # chat max output tokens
OLLAMA_JSON_NUM_PREDICT=2200       # JSON max output tokens
OLLAMA_TEMPERATURE=0.2             # chat temperature (JSON stays at 0.0)
```

## Run

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check: `GET http://127.0.0.1:8000/health`.
Model status: `GET http://127.0.0.1:8000/ml/model-status`.
