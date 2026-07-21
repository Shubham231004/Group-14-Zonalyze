# Zonalyze — Security Audit & Remediation Plan (Shubham branch)

> Audit of the **real** application on the `Shubham` branch (the latest code).
> Scope: find security vulnerabilities and hardening gaps, propose fixes that
> **do not change any user-facing feature or UI**. Written so junior models
> (Opus/Sonnet) can execute one item at a time.

## How the real system works (for context)

Single-page tabbed dashboard (`frontend/src/pages/dashboard.tsx`) where a user
enters a **municipality**, a **business type** (catalog or free-text resolved by
AI), and a **radius**, then gets: demographics (Statistics Canada 2021 features),
live competitor/transit/commercial POIs from **OpenStreetMap (Overpass API)**,
ML predictions (risk / revenue / feasibility via scikit-learn `.pkl` models),
lease/demand evidence, a recommendation, an **AI chat** (local **Ollama**), a
**market map** (Mapbox reverse-geocoding for addresses), site-address analysis,
and scenario history saved to Postgres + optional **MongoDB** cache.

Backend: FastAPI, ~40 routes in `backend/app/api/routes.py`. Frontend: React +
Vite + shadcn/ui, API base from `VITE_API_BASE_URL`.

**Nothing below proposes changing these features.** Every fix is invisible to the
end user or is an explicitly-flagged, approved change.

---

## Findings (ranked)

### 🔴 CRITICAL

**C1 — Hardcoded DB password in source + git history**
`backend/app/core/config.py:16` → `DB_PASSWORD = os.getenv("DB_PASSWORD", "sss@1008")`.
The literal password is the default and is present across git history
(`git grep "sss@1008" $(git rev-list --all)` → multiple commits). Anyone with
repo access has the DB credential.
Fix: remove the default (fail fast if unset), rotate the password, purge history
(team-coordinated). Feature impact: none.

**C2 — No authentication on any endpoint**
All ~40 routes in `routes.py` are public, including `DELETE /scenario-history`
(wipes saved data), `POST /ai/scenario-chat` (consumes CPU/GPU), and the OSM/geo
routes (make outbound third-party calls). Anyone who can reach the server can
call everything.
Fix: add auth (see recommendation) and protect all data/compute/geo/AI routes;
keep `/health` public. Feature impact: adds a login screen; existing screens
unchanged once signed in.

**C3 — Database connects as `postgres` superuser**
`config.py:15` defaults `DB_USER=postgres`. Any app compromise or injection =
full DB control. Fix: dedicated least-privilege role. Feature impact: none.

### 🟠 HIGH

**H1 — Prompt injection & unrestricted model choice in AI chat**
`ai_assistant_service.py` builds an Ollama prompt from the user's `question` and
`chat_history` with no separation/sanitization, and `ScenarioChatRequest.model`
lets the caller pick **any** Ollama model string (`schemas/ai_assistant.py:19`).
A crafted question can override instructions; an arbitrary model name can pull/
run unexpected local models. Fix: constrain/validate the model to an allowlist,
clearly delimit user content in the prompt, and treat AI output as untrusted.
Feature impact: none (chat still works; just safer).

**H2 — Internal error details leaked to clients**
- `/db-check` returns `str(e)` (`routes.py:82`, `db/test_connection.py`).
- `/storage/mongo-status` returns `f"...{exc}"` (`core/mongo.py:225`) — leaks
  Mongo host/URI/DNS internals.
- People/location fallback puts `str(exc)` into `meta.error`
  (`services/people_location_service.py:123`).
Fix: log full detail server-side, return generic messages. Feature impact: none.

**H3 — SQL echo leaks data to logs**
`db/session.py:5` `create_engine(..., echo=True)` prints every query + values.
Fix: gate behind a `DEBUG` env var, default off. Feature impact: none.

**H4 — No rate limiting on expensive/outbound endpoints**
`/ai/scenario-chat`, `/geo/osm-pois`, `/geo/market-map`, `/analyze-scenario`
each trigger heavy local compute or outbound calls (Overpass, Mapbox). Unlimited
+ unauthenticated = DoS and third-party quota/cost abuse. Fix: `slowapi` limits.
Feature impact: none under normal use.

**H5 — CORS not production-ready**
`main.py` hardcodes `allow_origins=["http://localhost:5173"]` with
`allow_methods=["*"]`, `allow_headers=["*"]`. Fix: env-driven allowlist, explicit
methods/headers. Feature impact: none (add real origin via env).

**H6 — No security headers / HTTPS posture**
No HSTS, CSP, `X-Content-Type-Options`, frame-ancestors, `Referrer-Policy`.
Fix: security-headers middleware; terminate TLS at the proxy. Feature impact: none.

**H7 — Unauthenticated outbound-request endpoints (abuse/SSRF-style)**
`/geo/osm-pois` and `/geo/market-map` cause the server to call Overpass/Mapbox
with user-supplied parameters and no auth/limit — usable as a free proxy / to
burn the Mapbox token quota. Overpass input has quotes stripped
(`osm_service.py:_tag_query`) which is good; the exposure is the open,
unthrottled trigger. Fix: auth + rate limit (covers H4/H7 together).

### 🟡 MEDIUM

**M1 — `requirements.txt` is UTF-16 encoded** (BOM + null bytes). `pip install -r`
fails on some systems. Fix: re-save UTF-8. Feature impact: none.

**M2 — No migrations** — schema via `create_all` (`db/init_db.py`). Adopt Alembic.

**M3 — ML models & data are untracked in git** — `.gitignore` excludes `*.json`,
`*.csv`, and `app/ml/models/` is not tracked, so a fresh clone/deploy has **no
models** → predictor raises `ModelsUnavailableError` → 503. Today it only works
because models exist on each machine locally. Fix: decide on a model-artifact
strategy (Git LFS, a release artifact, or a documented `train_models` step in
setup + CI). This is reproducibility/deployment risk, not a code change to features.

**M4 — In-memory message bus is unbounded & not thread-safe**
(`bus/messaage_bus.py`) — history list grows forever; shared singleton, no lock.
Fix: `deque(maxlen=...)` + lock. Feature impact: none.

**M5 — No structured logging / limited error handling** — only
`ModelsUnavailableError` is handled centrally; other unhandled exceptions return
raw 500s with stack traces. Fix: global handler + logging config.

**M6 — No automated tests, no CI** — nothing guards regressions. Fix: pytest
smoke tests (health, auth-required, analyze-scenario happy path) + GitHub Actions
(lint, test, pip-audit, npm audit, secret scan).

**M7 — Secrets sprawl, no `.env.example`** — `.env` holds DB, Mapbox, Mongo,
Ollama config with nothing documenting required vars. Fix: add `.env.example`
(names only, no values). Feature impact: none.

**M8 — Dependencies not audited** — run `pip-audit` / `npm audit` and patch
high/critical. (Frontend/Vite had known advisories in the other branch.)

### ⚪ LOW / HYGIENE

- **L1** Misspelled module `bus/messaage_bus.py` → rename to `message_bus.py`.
- **L2** `DELETE /scenario-history` has no auth/confirmation (folds into C2).
- **L3** Consider validating `municipality_name`/`business_subcategory` against
  the known catalogs server-side (defense in depth; catalogs already exist in
  `app/catalogs/` and `app/services/catalog_service.py`).

---

## Authentication recommendation: **Clerk** (managed) — don't hand-roll

Same rationale as a normal SaaS: password hashing, sessions, MFA, reset, and
breach handling are easy to get wrong. Clerk gives React components + JWTs the
FastAPI backend verifies against Clerk's JWKS. Fallback if you refuse a vendor:
the vetted `fastapi-users` library — never custom crypto. Auth is additive: one
sign-in screen in front; every existing tab/feature stays identical behind it.

---

## Remediation plan — phased, feature-preserving

Each phase is independent and shippable. **No phase changes the dashboard UI,
tabs, inputs, charts, AI chat, or map behavior.** The only new visible element in
the whole plan is the Clerk sign-in screen (Phase 2), and only when a Clerk key
is configured.

### Phase 0 — Baseline (safe, invisible)
- Fix `requirements.txt` → UTF-8 (M1).
- Add `backend/.env.example` + `frontend/.env.example` documenting every var (M7).
- Add pytest smoke tests + GitHub Actions CI (lint, test, pip-audit, npm audit,
  gitleaks) (M6, M8).
- Rename `messaage_bus.py` → `message_bus.py`, update the one import (L1).

### Phase 1 — Secrets & database
- Remove hardcoded password default; fail fast on missing creds (C1).
- Rotate the password + purge git history (team-coordinated; documented in SECURITY.md).
- Least-privilege DB role, off `postgres` (C3).
- `echo` driven by `DEBUG`, default off (H3).
- Introduce Alembic; stop using `create_all` (M2).

### Phase 2 — Authentication (Clerk)
- Backend `require_user` dependency (Clerk JWKS verification).
- Protect all data/compute/geo/AI/history routes; keep `/health` public (C2).
- Frontend `<ClerkProvider>` + sign-in gate + Bearer token on the existing API
  client (`frontend/src/services/api.ts`). No other UI change.

### Phase 3 — Hardening middleware (invisible)
- Env-driven CORS allowlist (H5).
- Security-headers middleware (H6).
- `slowapi` rate limits on AI/geo/analyze routes (H4, H7).
- Sanitize error responses: `/db-check`, `/storage/mongo-status`, fallback
  `meta.error` (H2).
- Bound + lock the message bus (M4).
- Global exception handler + structured logging (M5).

### Phase 4 — AI safety (invisible)
- Allowlist/validate `ScenarioChatRequest.model` (H1).
- Delimit user `question`/`chat_history` in the Ollama prompt; treat output as
  untrusted, keep the existing fallback path (H1).

### Phase 5 — Reproducibility & deploy
- Decide model-artifact strategy: Git LFS for `app/ml/models/`, or a documented
  `python -m app.ml.train_models` step in setup + CI, so a clean deploy has
  models (M3).
- Run `pip-audit` + `npm audit`; patch high/critical (M8).
- Document HTTPS/proxy deployment.

## Verification (per phase)
- Secrets: `git grep "sss@1008" $(git rev-list --all)` empty after purge; app
  refuses to boot without `DB_PASSWORD`.
- Auth: unauthenticated `POST /ai/scenario-chat` and `DELETE /scenario-history`
  return **401**; authenticated calls behave exactly as today.
- Rate limit: rapid calls return **429**.
- Errors: `/storage/mongo-status` and `/db-check` never contain host/URI/stack.
- Features: full manual click-through of every tab confirms identical behavior;
  smoke tests + `npm run build` green.

## Guardrail for whoever executes this
Do **not** alter dashboard layout, tabs, control inputs, charts, the AI chat, or
the map. If a security fix seems to require a visible change, stop and ask first.
