# ALI Simulations v0.10.1 — Session UX, Updates Feed & Peer Leadership Feedback

## Changes
- Organization-admin People directory now contains only active organization memberships. Disabled memberships remain in the Person access history/profile but disappear from the organization's active People list.
- Removed the `PA` avatar placeholder from page headers.
- Corrected birth month/year layout and matched control sizing on the consent gate.
- View As remains available only to Platform Administrators and Organization Administrators.
- Organization Administrator navigation includes buttons for active Sessions. Participant navigation now has a persistent left rail with active Sessions as first-class destinations.
- Improved visual delineation of tab navigation.
- Session dashboard now uses a 2/3 + 1/3 layout with a live Updates feed on the right.
- Updates feed includes partner needs, contributions, outreach, activities, and handoffs. All Session members can see general event updates across teams; handoffs are restricted to Organization/Platform Administrators and members of the assigned team.
- Handoffs are now optionally team-scoped.
- Added participant-to-teammate leadership feedback throughout active Sessions.
- Participants cannot evaluate themselves and can only rate current teammates.
- Every leadership capability may be left `Not observed`; null ratings do not count as zero.
- Repeated ratings from the same evaluator to the same teammate are averaged per capability before that evaluator contributes to the recipient's aggregate, preventing repeated submissions from giving one evaluator extra numeric weight.
- Closed/completed/archived Sessions remain read-only except to Platform Administrators.
- Fixed write guards for Partner Needs, Outreach, and Activities so closed Sessions are actually protected at API level.

## Database
Forward-only migration: `0009_peer_feedback_handoff_team`.

Adds:
- `session_handoffs.team_id`
- `leadership_peer_feedback`

No reset, truncate, or destructive production-data operation is included.
