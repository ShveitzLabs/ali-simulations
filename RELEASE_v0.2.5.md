# ALI Simulations v0.2.5

Render runtime/dependency compatibility update.

## Changes
- Explicitly sets `PYTHON_VERSION=3.13.7` in `render.yaml`.
- Retains root `.python-version` at `3.13.7`.
- Updates `psycopg[binary]` from `3.2.9` to `3.2.13`.
- Retains the free-web-service Alembic startup workaround.
- Retains PostgreSQL plan `0.1c-256mb`.

## Verify after deployment
The Render log should show Python 3.13.7 and should successfully install psycopg/psycopg-binary 3.2.13.
