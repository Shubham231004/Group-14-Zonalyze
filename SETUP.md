# Zonalyze — Setup Guide (for teammates)

How a teammate gets a working copy after `git clone` / `git pull`.

**Important — three kinds of things, delivered three different ways:**

| Thing | How you get it | Why |
|---|---|---|
| **Code** + small runtime data (feature CSVs, model metadata JSON) | `git pull` | tracked in git |
| **Secrets** (`backend/.env`, `frontend/.env.local`) | from a teammate, shared **securely** (password manager / DM) — NEVER via git | secrets must never be committed |
| **Large ML models** (`*.pkl`, ~347 MB) + raw training data | download from shared storage (or copy from a teammate) | too large for git |

So a teammate cannot get everything from `git pull` alone — they also need the
`.env` values and the model files. That is expected and correct.

## Steps

### 0. Prerequisites
- Python 3.13, Node 20, PostgreSQL running locally.

### 1. Get the code
```bash
git pull            # (or git clone <repo-url> the first time)
```

### 2. Backend
```bash
cd backend
python -m venv Zonalyze            # or reuse the shared venv name
# Windows: Zonalyze\Scripts\activate    macOS/Linux: source Zonalyze/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # for running tests (optional)

cp .env.example .env               # then fill in real values (see step 4)
```

### 3. Get the large model files (not in git)
The runtime feature CSVs and model metadata came with `git pull`, but the three
`.pkl` weight files did not. Get them one of two ways:
- **Download:** `MODELS_BASE_URL="<team storage URL>" python -m app.scripts.fetch_models`
- **Copy:** ask a teammate for their `backend/app/ml/models/*.pkl` and drop them
  into `backend/app/ml/models/`.

Without these, prediction endpoints return `503 models_unavailable`.

### 4. Secrets (`backend/.env`)
Ask a teammate (securely) for the values, or use your own local ones:
- `DB_PASSWORD` (required), `DB_USER`, `DB_HOST`, `DB_PORT`, `DB_NAME`
- Optional: `MAPBOX_ACCESS_TOKEN`, `MONGODB_URI`, `OLLAMA_*`
- Optional auth: `CLERK_ISSUER` (leave blank to keep auth off in dev)

### 5. Database
```bash
# create the database in PostgreSQL, then from backend/:
alembic upgrade head     # fresh DB  (use `alembic stamp head` if tables already exist)
python -m app.db.seed_demographics   # optional demo seed data
```

### 6. Frontend
```bash
cd ../frontend
npm ci
cp .env.example .env.local           # fill VITE_ values (optional Clerk/Mapbox)
```

### 7. Run
```bash
# terminal 1 (backend/, venv active)
uvicorn app.main:app --reload
# terminal 2 (frontend/)
npm run dev            # http://localhost:5173
```

### 8. Verify
```bash
cd backend && python -m pytest        # all tests should pass
```

## Keeping in sync going forward
- `git pull` gets new code + small data changes.
- Re-run `pip install -r requirements.txt` and `npm ci` when dependencies change.
- Re-run `alembic upgrade head` when there are new migrations.
- Re-fetch models only if the team publishes retrained ones.
