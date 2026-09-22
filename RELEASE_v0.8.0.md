# ALI Simulations v0.8.0 — Templates, Sessions, Reports, Consent & View-As

## Architecture
- Defines **Program/Simulation Templates** as reusable platform content and **Sessions** as organization-specific uses of a template.
- Platform Admin manages templates. Used templates archive instead of hard-delete; unused templates may be deleted.
- Organization Admin creates Sessions from entitled templates.
- Sessions own 1–4 teams, default named Team A–D, participant assignments, and role history.
- Belonging-style templates can default everyone to `team_member`; CityLab templates can use `auto_assign`. Role reassignment is modeled as time-based history so disruption-driven role changes can be added without losing prior state.

## Teams
- 1–4 teams per Session.
- Editable team names.
- Auto-balance endpoint plus manual participant/team/role overrides.
- Role assignment and team assignment remain separate.

## Reports
- Adds organization/platform summary reporting endpoint for Sessions, active Sessions, participant assignments, and consent records. This is the reporting foundation for richer Belonging and CityLab outcome reports.

## Consent
- Versioned consent templates and immutable signed consent records.
- Supports self/guardian signer metadata and session association.

## View As
- Platform Admin can view as any active defined user.
- Organization Admin can view as an active user in an organization they administer.
- Impersonation uses a short-lived token carrying the original administrator identity; `/api/auth/revert-impersonation` restores the administrator session.
- Start of impersonation is audit logged.

## Audit
- Audit API now returns 25 records per page, newest first, with total/pages metadata.
- Human-readable summaries and actor names are included directly in each row.
- Older activity remains available through pagination.

## Database safety
- Forward-only Alembic migration `0004_templates_sessions_consent`.
- No production tables are reset, truncated, or replaced.
- Existing v0.7 Belonging data is preserved.
