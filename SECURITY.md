# Zonalyze — Security Operator Guide

This file lists security-relevant steps that must be performed by a human
operator / the team, because they touch live secrets, the database, or shared
git history. Code-level hardening lands in the app; these steps do not.

## Phase 1 — required manual actions

### 1. Rotate the database password (IMPORTANT — do this)
The password `sss@1008` was committed to source and git history, so treat it as
compromised. Rotate it:
1. In PostgreSQL: `ALTER USER <user> WITH PASSWORD '<new-strong-password>';`
2. Update `backend/.env` → `DB_PASSWORD=<new-strong-password>`
3. Restart the backend.

The app no longer has a hardcoded fallback — it refuses to start unless
`DB_PASSWORD` is set (see `backend/app/core/config.py`).

### 2. Purge the old password from git history (team-coordinated)
Removing it from the current file is not enough; it still exists in history.
Rewriting history affects everyone, so coordinate with the team first.
- Recommended tool: `git filter-repo` (or BFG Repo-Cleaner).
- Example: `git filter-repo --replace-text <(echo 'sss@1008==>REMOVED')`
- Then force-push, and every teammate must re-clone or hard-reset.
- After rotation (step 1) the old value is useless anyway, but purge it so it
  is not indexed/leaked.

### 3. Create a least-privilege database role (replace the postgres superuser)
Do not run the app as the `postgres` superuser. Create a scoped role:
```sql
CREATE ROLE zonalyze_app LOGIN PASSWORD '<new-strong-password>';
GRANT CONNECT ON DATABASE zonalyze_db TO zonalyze_app;
GRANT USAGE ON SCHEMA public TO zonalyze_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zonalyze_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO zonalyze_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO zonalyze_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO zonalyze_app;
```
Then set `DB_USER=zonalyze_app` and the matching `DB_PASSWORD` in `backend/.env`.
(The app's default `DB_USER` is now `zonalyze_app` instead of `postgres`.)

## Database migrations (Alembic)

Alembic is now set up (`backend/alembic/`, `backend/alembic.ini`). Install deps
first: `pip install -r requirements.txt`.

- **Existing database** (tables already created by the old `create_all`): run
  **`alembic stamp head`** once — this marks the baseline migration as applied
  WITHOUT trying to recreate existing tables.
- **Fresh database**: run **`alembic upgrade head`** to create all tables.
- Future schema changes: edit the models, then
  `alembic revision --autogenerate -m "describe change"`, review the generated
  file, and `alembic upgrade head`.

Run all `alembic` commands from the `backend/` directory.
