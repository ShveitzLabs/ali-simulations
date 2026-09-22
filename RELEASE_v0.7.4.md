# ALI Simulations v0.7.4 — Complete UUID Annotation Fix

The prior hotfix corrected only some UUID annotations in `content.py`.

A full audit found remaining Pydantic models still annotated with the wrong UUID symbol:
- PartnerIn.organization_id
- ChallengeIn.organization_id
- TxIn.challenge_id
- OutreachIn.challenge_id

This release explicitly uses Python `uuid.UUID` for all API/Pydantic UUID annotations and route UUID parameters in `content.py`.

No database or migration changes.
