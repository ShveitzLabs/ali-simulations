# ALI Simulations v0.7.1 — Build Fix

Hotfix for v0.7.0.

- Fixes React/TypeScript build errors where async loader functions were returned directly from `useEffect`.
- `useEffect` callbacks now return `void`, as required by React.
- No database/schema changes.
- All v0.7.0 Belonging Operations & Network functionality is retained.
