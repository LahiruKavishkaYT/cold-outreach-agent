# Quick start (Windows / PowerShell)

## 1. Clone and open
```powershell
git clone https://github.com/<your-username>/outreach-studio-agent.git
cd .\outreach-studio-agent
code .
```
The `.claude\` folder must sit at the root of the folder you open in Claude
Code, so it finds the agents, skills, settings and hooks.

## 2. Check Python and run the tests
Hooks and scripts need Python 3.9+. The hooks find `python3`, `python` or
`py` on their own (Claude Code runs hooks through Git Bash on Windows, so Git
for Windows must be installed).
```powershell
python --version
python -m unittest discover -s tests
```
All 48 should pass. Skills call `python3 scripts/...` (that's the form the
settings pre-approve). Open Git Bash and run `python3 --version`; if it isn't
found, install Python from the Microsoft Store, which adds a `python3`
command.

## 3. Finish setup (once)
- `references\positioning-dealers.md`: Aria's demo number.
- `references\sender-profile.md`: postal address, then `require_footer: true`.
- Optional n8n webhook (Gmail **create draft** node only, no send node):
```powershell
$env:OUTREACH_COMPOSE_WEBHOOK = "https://YOUR-n8n-host/webhook/compose-draft"
```

## 4. Launch
```powershell
claude update
claude --model opus
```
The session opens with a briefing of what needs you.

## 5. Run
```text
/outreach new inputs/example-leads.csv --vertical medspa
/outreach-status
/reply aurora-medspa
/outreach sent aurora-medspa glow-lab-medspa
```

## What to expect
Claude researches up to 10 leads in parallel, drafts and reviews each, and
shows one batch card with every full email. Approve in your own words
("Approve the batch except #3"). It saves Gmail drafts; you send from Gmail,
then tell it "I sent 1-10" so dedup and follow-ups stay accurate.

## Changing the agent itself
`.claude\` and `scripts\` are read-only to Claude by default. To let it edit
them:
```powershell
$env:OUTREACH_MAINTENANCE = "1"; claude
```

## Behavioral evals
`claude plugin eval` needs a sandbox backend that native Windows doesn't
have; run it from WSL2. See docs\EVALS.md.
