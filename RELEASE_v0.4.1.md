# ALI Simulations v0.4.1 — Platform Administrator Bootstrap

- Creates the initial Platform Administrator if absent:
  - Jacob
  - jacob@providerenrichmentservices.org
  - temporary password: admin
- Adds a real platform sign-in screen.
- Forces the temporary password to be replaced on first sign-in.
- New passwords require at least 12 characters.
- Existing people/accounts are not overwritten by bootstrap.
- Keeps all existing PostgreSQL data and v0.4 organization functionality.

The temporary credential is intentionally transitional and should be changed immediately after deployment.
