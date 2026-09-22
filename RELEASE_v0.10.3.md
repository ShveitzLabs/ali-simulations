# v0.10.3 — Session Administration Fix & Participant Management

- Fixes Session admin save handling and replaces raw HTML/JSON parse failures with a useful API error.
- Adds Session Overview to creation and administration.
- Displays Session Overview plus start/end dates in the upper-right of every Session workspace.
- Adds organization-scoped participant candidate selection and Add to Session workflow.
- Keeps team reassignment and team rename controls in the Administrator tab.
- Makes the Administrator tab visually distinct with restrained red text/accent styling.
- Adds required start/end date-time controls to Session creation.
- Forward-only migration `0011_session_overview`; no destructive production reset.
