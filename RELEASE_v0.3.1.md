# ALI Simulations v0.3.1 — PostgreSQL Migration Fix

Fixes `DuplicateObject: type "licensestatus" already exists`.

The initial migration explicitly created PostgreSQL ENUM types and then table creation attempted to create those same types again. The four ENUM definitions now use `create_type=False`, while explicit `checkfirst=True` creation is retained.

The v0.3.0 testable interface is preserved.
