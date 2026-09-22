# ALI Simulations v0.10.4 — Session Date/Legacy Compatibility Fix

- Restores visible Start Date & Time and End Date & Time controls on Create Session.
- Adds Session Overview to the creation form.
- Requires and validates the Session schedule before creation.
- Avoids sending blank datetime strings to the API.
- Keeps legacy Sessions with null schedule/overview readable and editable.
- Fixes the Administrator tab so it does not request a nonexistent `/administrator` workspace endpoint.
- Synchronizes the Administrator editor after Session details are saved/reloaded.
- No schema migration and no destructive database operations.
