---
name: outreach-status
description: Show every lead's state, what needs the operator, follow-ups due, and per-campaign / per-angle reply metrics; or resume an interrupted lead at the right step. Read-only except for the resume hand-off. Use for "status", "where are we", "how's the campaign doing", "what's the reply rate", or "resume <lead>".
argument-hint: "[resume <lead-id>]"
allowed-tools: Read Glob Grep Bash(python3 scripts/*) Bash(python scripts/*)
---

# /outreach-status $ARGUMENTS

**Commands and paths:** the current working directory IS the outreach project
(it holds `scripts/`, `state/`, `data/`, `references/`). Resolve every relative
path in these instructions against the working directory, never against this
skill's base directory. Never `cd`. One script per Bash call, exactly
`python3 scripts/<name>.py <args>`, no chains or pipes. Read files with
Read/Glob/Grep, not cat/grep.

## Snapshot (computed before you read this)
!`python3 scripts/sync_state.py`
!`python3 scripts/pipeline_summary.py --metrics`

## With no argument
1. Report the stage counts and every lead needing action (awaiting approval,
   changes requested, blocked, expired), then follow-ups due.
2. Metrics per vertical / campaign / message_version: sent, replies, reply
   rate, positive, opt-outs, bounces. Under 30 sends per variant: report the
   numbers and say plainly that no conclusion is possible yet. Benchmarks for
   context are in the cold-email-craft skill's benchmarks reference.
3. Point to `outputs/dashboard.html` for the visual view.

## `resume <lead-id>`
Load the lead's state and re-enter the right skill at the right step, e.g.
`awaiting_final_approval` re-displays the full draft and waits for an
explicit decision; `changes_requested` re-enters the `draft-email` revision
loop.

Status never advances a lead. It only reports and resumes.
