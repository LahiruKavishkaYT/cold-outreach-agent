---
name: outreach
description: Main entry point for the outreach studio. Routes to batch or single-lead research and drafting, follow-ups, reply handling, logging manual sends, and status. Owns the lead state machine and the draft-only, human-approval workflow. Use for any request to run, continue, or check cold-email outreach for med spas or auto dealers.
when_to_use: The operator says things like "start the next batch", "/outreach new inputs/leads.csv", "draft emails for these leads", "I sent 1-10", "they replied", "where are we", or names a lead to work on.
argument-hint: "new <domain|inputs/*.csv> [--vertical medspa|dealers] | followup <lead-id> | reply <lead-id> | sent <lead-id ...> | status | resume <lead-id>"
allowed-tools: Read Glob Grep Bash(python3 scripts/*) Bash(python scripts/*)
---

# /outreach — router and workflow owner

**Commands and paths:** the current working directory IS the outreach project
(it holds `scripts/`, `state/`, `data/`, `references/`). Resolve every relative
path in these instructions against the working directory, never against this
skill's base directory. Never `cd`. One script per Bash call, exactly
`python3 scripts/<name>.py <args>`, no chains or pipes. Read files with
Read/Glob/Grep, not cat/grep.

Request: `$ARGUMENTS`

## Pipeline right now
!`python3 scripts/pipeline_summary.py`

Contract: `references/approval-policy.md` + `references/guardrails.md`. The
permanent rule in CLAUDE.md overrides everything: you never send, schedule,
forward or deliver email. Hooks enforce this; a hook denial is the system
working, so follow its reason and never route around it.

**Tracking:** every transition goes through `python3 scripts/log_update.py`
(it validates the transition and rebuilds the dashboard). Never edit
`state/leads-index.json` or `data/*` by hand; hooks block it anyway.

**Vertical:** every lead carries `vertical` (`medspa` | `dealers`). No
vertical, no drafting.

## Subcommands

### new <domain>  (single lead)
1. Derive `<lead-id>` (slug of the company or domain). Register it with its
   website so site-only research is allowed:
   `python3 scripts/log_update.py set <id> researching vertical=<v> website=<url> recipient=<email> campaign_id=<id> touch=first`
2. Run the `draft-email` skill for `<id>`.

### new <inputs/*.csv>  (batch of 10, the default for CSVs)
1. `python3 scripts/next_batch.py <csv> --size 10 --vertical <v> --campaign <id>`
   Deterministic pick (suppression, 14-day dedup, already-in-pipeline and the
   CSV's own "1st reach" column are pre-filtered). Exit 3 = missing verticals:
   ask the operator, don't guess.
2. Register each lead with `log_update.py set <id> researching vertical=... website=... recipient=... campaign_id=... batch_id=... touch=first message_version=<angle>`.
3. Research all 10 **in parallel** (one `lead-researcher` subagent each), then
   draft all 10 (`email-writer`), then review all 10 (`email-critic`). Move
   each lead through `researched -> drafting -> awaiting_final_approval` (or
   `blocked`) with log_update as you go.
4. Present ONE batch review card exactly per `references/batch-review.md`:
   summary table + every full body. Never summarize a body.
5. Wait for the operator's explicit batch approval in their own words. For each
   approved, CLEAR draft:
   - `python3 scripts/record_approval.py state/draft/<id>.json --text "<their exact sentence>"`
   - `python3 scripts/log_update.py set <id> approved_for_draft email_version=<N>`
   - `python3 scripts/gmail_draft.py state/draft/<id>.json`
   - `python3 scripts/log_update.py set <id> saved_as_draft`
   Held drafts -> `changes_requested` and the `draft-email` revision loop.
6. Don't start batch N+1 until every lead in batch N is settled
   (saved_as_draft / changes_requested / cancelled / blocked).

### followup <lead-id> -> `followup` skill
### reply <lead-id> -> `reply` skill

### sent <lead-id ...>
Only after the operator says they sent or scheduled them themselves:
`python3 scripts/log_update.py sent <id> [<id> ...]`. The script checks that
he said so in a prompt they typed; it refuses otherwise. This is the only path
to `sent_by_user`.

### status / resume -> `outreach-status` skill

## State machine (enforced by log_update.py)
```
researching -> researched -> drafting -> awaiting_review | blocked
 -> changes_requested -> revised -> awaiting_final_approval
 -> approved_for_draft (needs a logged approval) -> saved_as_draft
 -> ready_for_manual_send -> sent_by_user (only via `sent`) -> reply_received
 cancelled / expired reachable from pre-send states
```
Approved drafts expire after 7 days (`sync_state.py`, run by the SessionStart
hook).
