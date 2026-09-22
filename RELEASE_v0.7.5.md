# ALI Simulations v0.7.5 — UUID Namespace Collision Fix

Root cause: `content.py` imported Python `uuid.UUID` and then wildcard-imported the
models module. The models module exposes SQLAlchemy `UUID`, overwriting the Python
name at runtime. Pydantic therefore still received `sqlalchemy.sql.sqltypes.UUID`.

Fix:
- Python UUID is imported as `PyUUID`.
- Every UUID annotation/route parameter in `content.py` uses `PyUUID`.
- SQLAlchemy database column types remain unchanged in the models module.

No database or migration changes.
