# Zonalyze — Deployment & Reproducibility Guide

This covers what a new machine / production deploy needs, the pre-launch
security checklist, and the outstanding dependency notes. See `SECURITY.md`
for the one-time secret/database operator steps.

## 1. Reproducibility: ML models & data are NOT in git

The runtime depends on trained model artifacts and a processed feature file that
are **git-ignored** (they are large), so a fresh clone will not have them and the
prediction endpoints will return `503 models_unavailable` until they are present.

Current local footprint:

| Path | Size | Needed at… | In git? |
|---|---|---|---|
| `backend/app/ml/models/risk_classifier.pkl` | ~165 MB | runtime | no |
| `backend/app/ml/models/revenue_regressor.pkl` | ~173 MB | runtime | no |
| `backend/app/ml/models/feasibility_regressor.pkl` | ~9 MB | runtime | no |
| `backend/app/ml/models/feature_columns.json`, `model_metadata.json` | ~4 KB | runtime | no |
| `backend/app/data/processed/` | ~660 KB | runtime (census features) | no |
| `backend/app/data/raw/` | ~258 MB | training only | no |
| `backend/app/data/synthetic/`, `generated/` | ~28 MB | training only | no |

**Recommended strategy** (pick one — see the open question at the end):
- **Git LFS** for `backend/app/ml/models/*.pkl` — keeps them versioned with the
  repo. Note GitHub free LFS has 1 GB storage + 1 GB/month bandwidth; ~347 MB of
  models means a few clones can exhaust monthly bandwidth.
- **External object storage** (S3/GCS/Drive) — upload the `models/` folder and
  the processed feature file; download them at setup/deploy time via a script.
  Keeps the git repo small; best for the large raw data too.
- **Retrain on deploy** — run the training pipeline
  (`python -m app.ml.train_models`). Only viable if the training data is also
  available on the target machine (it is 286 MB and also git-ignored), so this
  still needs the data delivered somehow.

**Regardless of choice, track the two small runtime JSON files and the processed
feature file** (a few hundred KB) so the app has its feature schema on a clean
clone; only the large `.pkl` and raw data need the artifact strategy above.

## 2. Pre-launch security checklist

Everything below is already implemented in code and defaults to the safe/dev
behaviour; flip these on for a real deployment:

- [ ] **Rotate the DB password** and **create the least-privilege role** — see `SECURITY.md`.
- [ ] **Enable authentication:** set `CLERK_ISSUER` (backend) + `VITE_CLERK_PUBLISHABLE_KEY` (frontend). Verify unauthenticated API calls return 401.
- [ ] **Enable rate limiting:** set `RATE_LIMIT_ENABLED=true` (tune `RATE_LIMIT`). Watch for 429s under real traffic.
- [ ] **Set CORS origins:** `CORS_ALLOW_ORIGINS=https://your-production-domain` (comma-separated; no localhost in prod).
- [ ] **Serve over HTTPS** behind a reverse proxy (nginx/Caddy/managed platform). Terminate TLS there; the app already sends HSTS + security headers. Forward `X-Forwarded-*` so client IPs are correct for rate limiting.
- [ ] **Run migrations:** `alembic upgrade head` (fresh DB) or `alembic stamp head` (existing DB) — see `SECURITY.md`.
- [ ] **Keep `DEBUG=false`** in production (no SQL echo).
- [ ] Confirm no real `.env` is committed (`.gitignore` covers all `.env*` except `.env.example`).

## 3. Dependency audit (as of this phase)

**Frontend:** `npm audit` → **0 vulnerabilities** after `npm audit fix` (fixed
`@babel/core`, `brace-expansion`, `picomatch`, `postcss` — all build-time).

**Backend:** `pip-audit` — fixed the two libraries introduced for auth:
- `PyJWT` 2.10.1 → **2.13.0**
- `cryptography` 44.0.0 → **48.0.1**

Remaining advisories are in pre-existing pinned deps and are **recommended
follow-ups** (not done here to avoid breaking changes):
- `starlette` 0.52.1 — fixed in 1.x, but that requires a coordinated **FastAPI
  major upgrade**; schedule and test separately.
- `idna` 3.11 → 3.15, `click` 8.3.1 → 8.3.3 — low-risk transitive deps; bump
  with a full regression test.

Run audits regularly: `pip-audit -r backend/requirements.txt` and
`npm audit` (both are wired into CI as advisory steps).
