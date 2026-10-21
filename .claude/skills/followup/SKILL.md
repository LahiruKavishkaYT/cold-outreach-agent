---
name: followup
description: Draft the next follow-up (F1/F2/F3) for a lead that was sent a first touch and hasn't replied, through the same approval gate as first-touch. Checks for replies and opt-outs first. Never schedules or auto-sends a sequence. Use when the operator asks for follow-ups or the session briefing lists follow-ups due.
argument-hint: "<lead-id>"
allowed-tools: Read Glob Grep Bash(python3 scripts/*) Bash(python scripts/*)
---

# /followup

**Commands and paths:** the current working directory IS the outreach project
(it holds `scripts/`, `state/`, `data/`, `references/`). Resolve every relative
path in these instructions against the working directory, never against this
skill's base directory. Never `cd`. One script per Bash call, exactly
`python3 scripts/<name>.py <args>`, no chains or pipes. Read files with
Read/Glob/Grep, not cat/grep.

Lead: `$ARGUMENTS`. If that's more than a bare lead id, pull the lead id out
of it (ids look like `aurora-medspa`; check `state/leads-index.json`). Below,
`<lead>` means that id.

## 1. Guard checks
- Lead has `reply_received` or any `outcome`: no cold follow-up. Route to `reply`.
- `python3 scripts/suppression_check.py <recipient>` non-zero: STOP.
- `followups_sent` is already 3: stop. The lead rests 90 days.

## 2. Pick the rung (references/email-craft.md)
| rung | when | content |
|---|---|---|
| F1 | +3-4 days after first touch | new value: offer the 2-minute Loom |
| F2 | +5-7 days after F1 | a different angle from the vertical file (dealers: out-of-state/financing; med spa: after-hours consult questions) |
| F3 | +7 days after F2 | short, honest close-the-loop ("If timing's wrong, one line and I'll stop.") |
See the cold-email-craft skill's follow-up reference for angle rotation and
breakup-email examples. Never "just following up".

## 3. Draft -> critic -> review -> approve -> Gmail draft
`log_update.py set <lead> drafting touch=followup`, then run `draft-email`
from step 3. Follow-ups are threaded replies, so the writer sets
`touch: "followup"` (links allowed if the operator asks; the Loom link is the usual
one). A previously approved follow-up template does not approve this
personalized version.

## 4. Never automatic
There is no timer that sends. Each follow-up is generated on request,
reviewed, approved, and left as a Gmail draft for the operator.
