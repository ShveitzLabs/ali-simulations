# ALI Simulations v0.8.1

Corrective release for v0.8 template/session setup.

- Platform Admin can edit existing program/simulation templates.
- Belonging templates can define supported collection categories: Food, Toys, Clothing, School Supplies, Hygiene Essentials, Winter Warmth, and Other/Custom.
- Monetary donations can be enabled/disabled per supported category.
- Template configuration is persisted as JSON via forward-only migration 0005.
- Session creation now loads every active organization the current user actually administers (all active organizations for Platform Admin), rather than assuming the first membership.
- Template choices are filtered by the selected organization's enabled simulation entitlements.
- Team count respects the selected template's maximum-team setting.
- Existing production data is preserved; no reset/truncate operations.
