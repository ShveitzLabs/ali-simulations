# ALI Simulations v0.7.3 — Pydantic UUID Hotfix

Fixes startup failure in `backend/app/api/content.py`.

Root cause: Pydantic request models were annotated with SQLAlchemy's `UUID` column type.
Pydantic cannot generate a request schema for `sqlalchemy.sql.sqltypes.UUID`.

The API models now use Python's `uuid.UUID` (aliased as `PyUUID`) for request annotations.
SQLAlchemy UUID types remain unchanged for database columns.

No database/migration changes.
