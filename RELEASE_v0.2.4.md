# ALI Simulations v0.2.4

Complete repository package with a pinned Python runtime for Render.

## Changes
- Adds root `.python-version` with `3.13.7`.
- Prevents Render from automatically selecting Python 3.14.x.
- Retains the existing tested dependency pins, including `psycopg[binary]==3.2.9`.
- Retains the Render free-web-service migration workaround.
- Retains PostgreSQL plan `0.1c-256mb`.

## Expected Render build log
On the next build, Render should report Python 3.13.7 instead of Python 3.14.3.

Upload the contents of this folder to the repository root while preserving directories.
