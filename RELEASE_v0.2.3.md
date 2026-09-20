# ALI Simulations v0.2.3

Complete repository package based on v0.2, with Render deployment fixes incorporated.

## Render fixes
- Removed unsupported `preDeployCommand` from the free web service.
- Alembic migrations run in `startCommand`.
- PostgreSQL plan remains `0.1c-256mb` and is not downgraded.
- Full `backend/` and `frontend/` application trees are included.

## GitHub upload
Upload the *contents* of this folder to the repository root. The repository root must directly contain `backend/`, `frontend/`, `render.yaml`, and the other top-level files.
