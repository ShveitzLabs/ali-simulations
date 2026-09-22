# ALI Simulations v0.10.2 — Identity Cues, Session Administration & Narrative Feedback

- Adds `Welcome, [First Name]` beneath the application logo for authenticated users.
- Adds plain-language page purpose text across the application shell and Session workspace.
- Session creation now requires start and end date/time.
- Organization Administrators receive a Session Administrator tab for schedule changes, team renaming, and participant reassignment.
- Leadership peer aggregation remains scoped to a single Session: repeat ratings from the same evaluator for the same participant/capability are averaged inside that Session only; ratings are never averaged across Sessions.
- Team Feedback lists eligible teammates (or Session participants for administrators), excludes self-evaluation, and supports Not Observed/null scores.
- Peer and formal evaluations now include a narrative text field for every leadership capability.
- Forward-only migration `0010_evaluation_narratives`; no destructive data reset.
