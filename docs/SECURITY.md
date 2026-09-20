# Security Baseline

- Passwords are never viewable or recoverable. Store salted password hashes only.
- Administrators may force/reset passwords within authorized scope; actions are audited.
- MFA is required for Platform Administrators and should be supported for other privileged roles.
- Least-privilege RBAC is enforced server-side, not only in the UI.
- Every tenant-scoped query must enforce organization boundaries.
- Secrets belong in environment variables/secret management, never Git.
- HTTPS/TLS in production.
- Sensitive administrative changes are audit logged.
- Signed consent artifacts and uploads belong in private object/document storage; PostgreSQL stores authoritative metadata/references.
- Subscriber exports expose curated summaries, not schema, internal identifiers, trigger logic or raw database tables.
- Expiration/suspension never deletes historical data.
