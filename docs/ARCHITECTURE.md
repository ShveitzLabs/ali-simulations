# ALI Simulations Architecture

## Product hierarchy
**Platform → Organization → Simulation Type → Scenario → Scenario Version → Session → Teams / Assignments → Actions / Evidence → Outcomes**

ALI Simulations is a multi-tenant leadership simulation platform. Belonging and CityLab are modules on shared platform services rather than separate applications.

## Technology
- React + TypeScript frontend
- FastAPI backend
- PostgreSQL
- SQLAlchemy + Alembic
- Render deployment target
- Provider-independent email and object-storage service layers

## Core rules
1. Organization data is tenant-scoped.
2. People are canonical and unique by normalized email.
3. Organization membership controls tenant-specific access and expiration.
4. Organization and membership expiration are nullable; NULL means no expiration.
5. Simulation entitlement is granted per organization by Platform Admins.
6. Scenario design/publishing is Platform-Admin-only.
7. Published scenario versions are immutable.
8. Development sessions are explicitly flagged and excluded from production analytics.
9. Operational records should inherit session development state.
10. Historical records are archived/retained rather than silently overwritten.
11. Subscriber exports are curated outputs, not raw database/table exports.
