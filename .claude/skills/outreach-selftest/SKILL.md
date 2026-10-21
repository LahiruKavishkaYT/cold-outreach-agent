---
name: outreach-selftest
description: Health check for the outreach studio itself. Runs the free deterministic test suite (gates + hooks + injection payloads), verifies the approvals log chain, audits every existing draft against the current gates, and explains how to run the paid behavioral evals. Use after editing guardrails, positioning files, scripts or hooks, after a Claude Code or model update, or when something seems off.
disable-model-invocation: true
allowed-tools: Read Bash(python3 -m unittest *) Bash(python -m unittest *) Bash(python3 scripts/*) Bash(python scripts/*)
---

# /outreach-selftest

Run these and report a short pass/fail summary with anything that needs the operator:

1. Deterministic suite (free, ~5 seconds, no model calls):
   `python3 -m unittest discover -s tests -v`
2. Approval log integrity: `python3 scripts/verify_approvals.py`
3. Draft audit against the current gates:
   `python3 scripts/audit_drafts.py --only-unsent --md outputs/draft-audit.md`
4. Behavioral evals are paid model runs, so don't start them; tell the operator the
   command (from a terminal at the project root):
   `claude plugin eval . --scaffold --allow-tools Write Edit "Bash(python3 scripts/*)" --runs 1 --ablation none`
   and that `docs/EVALS.md` explains cost, cases and CI.

If a unit test fails, show the failing test name and assertion. Don't edit
scripts or hooks to make a test pass (they are read-only to the agent unless
Claude Code was launched with `OUTREACH_MAINTENANCE=1`).
