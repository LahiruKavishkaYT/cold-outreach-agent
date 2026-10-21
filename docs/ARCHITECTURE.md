# Architecture: how "never send, only the operator approves" is enforced

v2 stated the rules well but relied mostly on the model following them. The
v2 approvals log shows the gap: it accepted "sended", "approved this" and "i
scheduled all the emails to june 30th..." as approvals, because nothing
checked the wording or who typed it. v3 puts each rule behind code.

## Layers

| layer | what | can the model bypass it? |
|---|---|---|
| 0. Capability | No send credentials exist. The only outbound call is `gmail_draft.py` to an n8n webhook with a Gmail *create draft* node. | No: there is nothing to call. |
| 1. Permissions | `settings.json` allows `python3 scripts/*`, writes to `state/research`, `state/draft`, `outputs`. Denies curl/wget/sendmail/smtp. | Only by asking you, and hooks still apply. |
| 2. Hooks | Inspect every tool call before it runs (below). Fail closed. | No: they run outside the model. |
| 3. Gate scripts | Deterministic exit codes: `precheck.py` and friends. | No: you can't pass a gate by claiming it passed. |
| 4. Trust anchors | Operator log (what you typed) + hash-chained approvals log. | No: write-protected by hooks; chain detects edits. |
| 5. Prompts | CLAUDE.md, skills, agents. | They're guidance; layers 0-4 catch mistakes. |

## Hooks (`.claude/hooks/`, wired in `.claude/settings.json`)

| event | hook | does |
|---|---|---|
| SessionStart | `session_start.py` | runs `sync_state.py` (expiries), verifies the approvals chain, injects a briefing: counts, what needs you, follow-ups due, setup gaps |
| UserPromptSubmit | `capture_operator_input.py` | logs each prompt you type to `data/.operator/prompts.jsonl`; tags long or email-looking prompts as `paste` |
| PostToolUse(AskUserQuestion) | same | logs the answers you click (not the question text, which the model wrote) |
| PreToolUse(Bash) | `guard_bash.py` | denies network/mail tools, inline interpreter code that imports network libs, any touch of the approvals/operator logs or hook config, shell writes into `data/`/`state/`, inline `OUTREACH_*` overrides, edits to `scripts/`/`.claude/` |
| PreToolUse(Write/Edit) | `guard_files.py` | denies writes to the logs, the index, suppression and send logs (scripts only), hand-written approval fields, in-place edits of an approved draft version, and edits to the enforcement layer |
| PreToolUse(WebFetch) | `guard_webfetch.py` | allows only hosts that are known lead websites (index, batch manifests, research files, CSV website columns, `allowed-research-domains.txt`) |
| PostToolUse(Write/Edit) | `post_draft_lint.py` | runs the gates on a just-written draft and hands FAIL/WARN notes back so the writer fixes them before review |

All hooks go through `run.sh`, which finds `python3`, `python` or `py`, so
they work in Git Bash on Windows.

Guards fail **closed**: if a guard crashes, the call is denied. Context hooks
fail **open**: a briefing error never blocks your session.

## Gates (`scripts/precheck.py`)

| gate | hard/advisory | notes |
|---|---|---|
| suppression | hard | full addresses and `@domain` lines |
| dedup | hard | 14-day window over `data/outreach-log.json` |
| placeholder | hard | `{{x}}`, `[NAME]`, `TODO`, `[[MISSING]]`, `<first_name>` |
| demo number | hard | number must be **this lead's vertical's** canonical demo; v2 accepted any vertical's number |
| content | hard | recipient format, banned phrases (parsed from guardrails.md), links in first touch, footer when required |
| content | advisory | word count per touch, subject length/case, >1 question, em dashes, emoji, AI-tell patterns, missing footer |
| links | advisory | malformed / example domains |

## State machine (`scripts/log_update.py`)
Transitions are a whitelist. `approved_for_draft` needs a logged approval for
that draft's hash. `sent_by_user` is only reachable via `log_update.py sent`,
which needs a send/schedule confirmation you typed in the last 12 hours.
Opt-out and negative replies append to suppression automatically.

## Known limits (honest list)
- A determined human with shell access can edit anything; this protects
  against model mistakes and prompt injection, not against you.
- `record_approval.py` checks that your approval words appear in a recent
  prompt, not which draft you meant. The batch card numbers drafts and Claude
  echoes the mapping back before recording; read it.
- `guard_bash.py` is pattern-based. It covers the common shells and
  languages; the permission layer (allow-list) is the backstop.
- Reconciling against the Gmail Sent folder (approval-policy §Send
  reconciliation) is still manual: there's no inbox access by design.
