# Contributing

Thanks for helping out. A few ground rules keep this project safe.

## Non-negotiables
- **No send path.** PRs that add sending, scheduling, forwarding or any
  outbound delivery besides creating a draft will be closed.
- **Don't weaken a gate or hook without a test.** If you change
  `scripts/*_check.py`, `precheck.py` or `.claude/hooks/*`, add or update a
  test in `tests/` showing the new behavior.
- **No real lead data.** Fixtures use `.example` domains and `555` phone
  numbers. Never commit anything from `data/`, `state/`, `outputs/` or a
  real CSV.

## Development
```bash
python3 -m unittest discover -s tests     # must stay green
```
Python stdlib only; please don't add dependencies.

To let Claude Code edit `.claude/` or `scripts/` while you work, launch it with
`OUTREACH_MAINTENANCE=1`.

## Behavioral evals
New guardrail behavior should come with an eval case in `evals/<case-name>/`
(`case.yaml`, `prompt.md`, `graders/`, `scaffold.sh`). See
[docs/EVALS.md](docs/EVALS.md).

## Pull requests
- One focused change per PR, with a clear description of why.
- Update `CHANGELOG.md` and any affected docs.
- Run the test suite before opening the PR.

## Reporting a security issue
If you find a way to bypass the approval or send guards, please open an issue
titled "Guard bypass" with only a short summary, without a working exploit,
and ask a maintainer for a private channel to share the details.
