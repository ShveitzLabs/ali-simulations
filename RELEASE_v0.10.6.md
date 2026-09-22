# v0.10.6 — Viewport-First Session Workspace

- Reworked the Session workspace header into a compact application context band rather than a page-sized header.
- Session name, team/role, overview, dates, and tabs now consume roughly 1–2 inches vertically on a standard desktop viewport.
- Session overview is limited to four visible lines in the workspace header.
- Removed the redundant standard page header from Session workspaces.
- Dashboard and Updates feed use the remaining viewport height; overflowing panel content scrolls internally instead of forcing the browser page to scroll.
- No database migration or data changes.
