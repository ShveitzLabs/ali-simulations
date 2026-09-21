# ALI Simulations v0.5.0 — People + Organization Onboarding

## Fixes
- Fixes organization creation bug caused by passing the organization name twice to the SQLAlchemy model.
- Replaces generic `Request failed` UI with API validation/authentication/database messages.

## Organization onboarding
- Adds organization email and phone.
- Creates/reuses an initial Organization Administrator by normalized email.
- Creates organization membership and assigns the Organization Administrator role.
- Existing Person records are reused rather than duplicated.

## People
- Functional searchable People directory.
- Add, view, and edit Person records.
- Email remains the platform-wide unique identity/username.
- Person profile shows login status, platform-admin status, organization memberships, and organization roles.
- Adds optional person phone number.

## Data safety
- Uses forward-only Alembic migration 0002.
- Existing PostgreSQL rows are preserved.
- Administrative creates/updates continue to be audited.
