# ALI Simulations v0.2 — Authentication + Core Database

React + TypeScript frontend, FastAPI backend, PostgreSQL, SQLAlchemy and Alembic.

## v0.2 adds
- Initial Alembic migration for the core schema
- Argon2 password hashing; existing passwords are never viewable
- JWT login and authenticated `/api/auth/me`
- Bootstrap Platform Administrator from environment variables
- Eight core roles plus granular permission catalog
- Simplified Render deployment: one web service serves FastAPI + the built React SPA, plus PostgreSQL
- Pre-deploy database migrations and database-aware `/api/health`
- Authenticated React login/dashboard

## Render
Sync the root `render.yaml`. On initial Blueprint creation Render asks for `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`. `SECRET_KEY` is generated and `DATABASE_URL` comes from the managed database.

The bootstrap account is only created if that email does not already exist. Do not use real participant data yet.

## Security
Never commit `.env` or credentials. Admins will be able to reset passwords, but no role will ever be able to retrieve/view an existing password. License/access expiration fields default to `NULL` (no expiration). Scenario authoring remains Platform-Admin-only.


## Current release
v0.8.2 — Identity, Access, Privacy & Consent hardening. See RELEASE_v0.8.2.md.
