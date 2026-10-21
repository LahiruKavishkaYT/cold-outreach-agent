# Changelog

## v3.0.0 (2026-10-21)

### Enforcement moved from prompts into code
- **Hooks** (new, `.claude/hooks/`): SessionStart briefing, UserPromptSubmit
  operator log, Bash/file/WebFetch guards, post-write draft lint. Guards fail
  closed. See docs/ARCHITECTURE.md.
- **Approval can only come from you.** `record_approval.py` now requires
  explicit wording AND that the words appear in a prompt you typed (operator
  log) AND a clear precheck. It writes the approval fields itself and
  appends a hash-chained log line (`verify_approvals.py` detects edits). v2
  accepted any text: the log contains "sended" and "approved this".
- **Pasted prospect text can't approve.** Long or email-shaped prompts are
  logged as `paste` and ignored for approval and send confirmation.
- **`gmail_draft.py`** also requires the hash in the approvals log and an
  unexpired approval.
- **State machine enforced** in `log_update.py` (whitelisted transitions;
  `approved_for_draft` needs a logged approval; `sent` needs your typed
  confirmation; `negative` replies now auto-suppress like `optout`).
- **Site-only research enforced** by `guard_webfetch.py`.
- **Self-protection:** `.claude/`, `scripts/`, `guardrails.md` are read-only
  to the agent unless launched with `OUTREACH_MAINTENANCE=1`.

### Gate fixes (bugs found while writing tests)
- `demo_number_check.py` accepted any vertical's demo number, so Mia's
  med-spa number on a dealer email passed. Now vertical-aware.
- Phone detection read model years and model names ("the 2019 911",
  "2018-2021 models") as phone numbers and blocked good dealer drafts. Now
  matches real phone shapes (US/CA/AU) only.
- New `content_check.py` (hard): recipient format, banned phrases (parsed
  from guardrails.md, so the list is finally enforced), links in a first
  touch, compliance footer when required. Advisory: length, subject, CTA
  count, em dashes, emoji, AI tells.
- Suppression supports `@domain` lines.
- Dashboard read `index["leads"]` while `log_update.py` writes a flat index,
  so it always showed 0 leads. Fixed; now shows all 80.

### Data repair (`scripts/migrate_v3.py`, applied; backup in `backups/`)
- 41 dealer sends lived only inside draft JSON; `data/outreach-log.json` was
  empty, so **dedup could not see any of them**. Backfilled.
- 61 leads existed in `state/draft/` but not the index; registered.
- All 73 drafts got an explicit `vertical` (not part of the hash, so no
  approval was voided). The 7 side-index dealer leads were merged.

### Skills and agents
- Vendored **cold-email-craft** (coreyhaines31/marketingskills cold-email
  v2.2.0, MIT) with house overrides; preloaded into all four subagents.
- Current frontmatter everywhere: `when_to_use`, `allowed-tools`,
  `disable-model-invocation`, `user-invocable`, `` !`cmd` `` dynamic context;
  agents get `disallowedTools`, `skills`, `effort`, `maxTurns`, `color`.
- lead-researcher moved to Sonnet (10 run in parallel per batch; extraction
  doesn't need Opus). Writer, critic, reply-analyst stay on Opus.
- email-critic got a fixed 0-100 rubric; reply-analyst uses the upstream
  reply taxonomy and maps it to `log_update.py outcome` values.
- New `/outreach-selftest`. `/outreach-status` shows reply rate per
  vertical / campaign / `message_version`.
- Skills take `$ARGUMENTS` and extract the lead id (a named-argument version
  grabbed "approve" as the lead id in the first eval run).
- Skills and agents say explicitly: resolve paths against the project, never
  `cd`, one `python3 scripts/...` per Bash call (the first eval runs showed
  the model `cd`-ing into the skill folder and chaining commands).

### Copy rules
- Subject lines 2-5 words (was 4-8; 31 of 73 drafts ran 7+ words).
- No em dashes (45 of 73 drafts had them; top AI tell).
- Drafts carry `vertical`, `touch`, `message_version`.
- New `references/sender-profile.md` (postal address + opt-out, CAN-SPAM)
  and `references/allowed-research-domains.txt`.

### Fixed contradictions
- CLAUDE.md and guardrails.md said the only proof is Mia, which contradicts
  the dealer campaign. Now vertical-specific.
- README mentioned "Jack" (an HVAC demo from an older offer). Removed.
- CHANGELOG said "one lead at a time; no bulk approval", which predates the
  batch flow.

### Tests and evals
- `tests/`: 48 stdlib unittest cases for gates, approval, state machine,
  hooks (including injection and tamper payloads).
- `evals/`: 9 `claude plugin eval` cases with fixtures (see docs/EVALS.md).
- `.claude-plugin/plugin.json` so the harness can load the agent.

### Not changed
Positioning/offer content, the batch review card format, the n8n compose
contract, `next_batch.py` selection logic (except domain suppression and
email validation), and your existing drafts' text.

## v2 (2026-07)
Two verticals (med spa, dealers), batches of 10, batch review card,
auto-tracking via `log_update.py`, dashboard.

## v1.0.0
Initial release: research, draft, deterministic gates, hash-anchored
approval, Gmail compose webhook with local fallback.
