# ALI Simulations v0.8.2 — Identity, Access, Privacy & Consent

## Included
- Person screen access/membership management foundation with organization role changes and enable/disable behavior.
- Scoped People APIs for Organization Administrators; cross-tenant people are not enumerable or retrievable.
- Organization-scoped contact provenance so contact details supplied by one organization are not automatically exposed to another.
- Add-person workflow silently reuses canonical people by normalized email while exposing only authorized organization-scoped data.
- Platform-level role management endpoint restricted to Platform Administrators.
- View As hardening: Organization Administrators cannot View As Platform Administrators or inherit administrator scope outside organizations they administer; persistent Revert to Admin control in navigation.
- Platform-managed consent only; organization consent administration removed from normal navigation.
- Login consent gate for new and existing users without current consent.
- Birth month/year collection and conservative 18+ determination; uncertain/minor cases require guardian consent.
- Optional consent review modal; viewing text is not required before agreement.
- Default platform Participation Consent seeded by migration.
- Guardian consent recording endpoint for Platform Administrators.
- Forward-only Alembic migration 0006; no production data reset.

## Validation
- All backend Python and Alembic files pass Python compilation.
- Frontend production compilation could not be completed locally because React/react-router dependencies are not installed in this runtime. Render should perform dependency installation/build.
