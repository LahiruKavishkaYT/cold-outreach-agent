# Skills: what's used, where it came from, what was rejected

## In this repo

| skill | type | invoked by | purpose |
|---|---|---|---|
| `outreach` | workflow | you (`/outreach`) or Claude | router, batch pipeline, state machine |
| `draft-email` | workflow | `/draft-email`, router | single-lead loop through approval |
| `followup` | workflow | `/followup` | F1-F3 ladder |
| `reply` | workflow | `/reply` | untrusted reply handling |
| `research-lead` | workflow | `/research-lead` | site-only research |
| `outreach-status` | workflow | `/outreach-status` | pipeline + metrics (dynamic context) |
| `outreach-selftest` | maintenance | you only (`disable-model-invocation`) | tests, log check, draft audit |
| `cold-email-craft` | knowledge | preloaded into all 4 subagents (`user-invocable: false`) | craft, AI tells, reply taxonomy, deliverability |

Frontmatter now uses current Claude Code fields: `when_to_use`,
`argument-hint`, `allowed-tools` (pre-approves `python3 scripts/*` so a skill
run doesn't prompt), `disable-model-invocation`, `user-invocable`, and
`` !`command` `` dynamic context (status and router skills inject a live
pipeline snapshot before Claude reads them). Agents use `tools` +
`disallowedTools`, `skills` (preload), `model`, `effort`, `maxTurns`, `color`.

## Vendored: cold-email-craft
- Source: [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills)
  `skills/cold-email` v2.2.0, plus `copywriting/references/ai-tells.md` and
  `prospecting/references/local-prospecting.md`. MIT license, kept in
  `.claude/skills/cold-email-craft/upstream/LICENSE`; commit pinned in
  `upstream/SOURCE.txt`.
- Why this one: the most-installed and most-maintained cold-email skill found
  (updated 2026-10-19), it ships its own evals, and its rules (peer voice,
  one low-friction ask, short lowercase subjects, AI-tell blacklist, reply
  taxonomy, deliverability rules) match your playbook.
- What was changed: a house-overrides section that wins over upstream:
  demo-only proof, no booking links, facts only from research, nothing sends,
  2-5 word subjects. Upstream files are verbatim so they can be refreshed.
- Refresh: re-clone the repo and copy the same files into `upstream/`; read
  the diff before keeping it.

## Already in your account, used as references (not copied)
These came up in the search and overlap with this agent. They're good for
one-off work but would conflict with the approval gate if wired in:
- `sales:draft-outreach`, `small-business:outreach-composer`,
  `marketing:email-sequence`: general drafting with no hash/approval trail.
- `anthropic-skills:skill-creator`: has its own `evals/evals.json` format for
  iterating on one skill. This repo uses `claude plugin eval` instead (native,
  baseline comparison, CI exit codes); the two formats don't read each other.
- `anthropic-skills:hormozi-offer-builder`: the positioning files were built
  with this; use it when you rework an offer, then paste results into
  `references/positioning-<vertical>.md`.

## Evaluated, not adopted
- `mattpocock/skills` `git-guardrails-claude-code` (490K installs): a
  PreToolUse hook that blocks dangerous git commands. Same pattern as
  `guard_bash.py`; nothing git-specific needed here.
- `mattpocock/skills` `writing-great-skills` / `writing-for-agents`: style
  guidance applied while rewriting the skills, not shipped.
- Other cold-email skills on skill directories (`humanizerai/agent-skills`,
  `alirezarezvani/claude-skills`, `paramchoudhary/resumeskills`): smaller,
  less maintained, or job-seeker focused.
- `skills.sh` CLI search (`npx skills find`) was blocked from the build
  environment's network, so the leaderboard was read via the web instead.
