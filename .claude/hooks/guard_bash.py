#!/usr/bin/env python3
"""PreToolUse(Bash) guard. Blocks every shell path that could send mail, reach
the network, tamper with the trust anchors, or redirect the gates.

The permission deny-list in settings.json is a first layer; this hook is the
second, and it inspects the WHOLE command (pipelines, subshells, heredocs),
which prefix-based permission rules can't.
"""
import re
import sys
from hooklib import read_input, deny, guard, maintenance_mode

SENDERS = re.compile(
    r"(?<![\w./-])(curl|wget|invoke-webrequest|iwr|invoke-restmethod|irm|nc|ncat|netcat|telnet|"
    r"ssh|scp|sftp|ftp|sendmail|mailx|mutt|msmtp|swaks|ssmtp|gcloud|gsutil|gh|aws)(?![\w-])", re.I)
MAILISH = re.compile(r"\bmail\s+-s\b|smtp|messages\.send|drafts\.send|users\.messages|gmail[^\n]{0,40}\bsend\b|"
                     r"send_?mail|sendgrid|mailgun|postmarkapp|api\.resend\.com", re.I)
INLINE_CODE = re.compile(r"\b(python3?|py|node|deno|bun|ruby|perl|php|pwsh|powershell)(\.exe)?\b[^|;&]*?"
                         r"(\s-c\b|\s-e\b|\s-\s*<<|<<|\s-command\b)", re.I)
NETWORK_CODE = re.compile(r"urllib|requests|http\.client|httpx|aiohttp|smtplib|imaplib|socket|fetch\(|axios|"
                          r"net/http|LWP|Net::|WebClient|System\.Net", re.I)
PROTECTED = re.compile(r"approvals\.log|\.operator|prompts\.jsonl|\.claude[/\\](settings|hooks)", re.I)
DATA_WRITE = re.compile(r"(>>?|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bdel\b|\bremove-item\b|"
                        r"\bset-content\b|\bout-file\b)\s*[^|;&<>]*?(?<![\w])(data|state)[/\\]", re.I)
ENV_OVERRIDE = re.compile(r"\b(OUTREACH_ROOT|OUTREACH_COMPOSE_WEBHOOK|OUTREACH_MAINTENANCE|CLAUDE_PROJECT_DIR)\s*=", re.I)


def main():
    inp = read_input()
    cmd = ((inp.get("tool_input") or {}).get("command") or "")
    low = cmd.lower()
    if not cmd.strip():
        return

    if SENDERS.search(cmd) or MAILISH.search(cmd):
        deny("Blocked: this command could send mail or reach the network. Outreach is "
             "draft-only; the only outbound path is `python3 scripts/gmail_draft.py` after "
             "a recorded approval. (outreach guard_bash)")
    if INLINE_CODE.search(cmd) and NETWORK_CODE.search(cmd):
        deny("Blocked: inline interpreter code with network/mail libraries. Use the "
             "scripts/ gates instead. (outreach guard_bash)")
    if PROTECTED.search(cmd):
        deny("Blocked: the approvals log, the operator log and the hook config are "
             "tamper-protected. Use the Read tool to view them; only scripts/record_approval.py "
             "and the hooks write them. (outreach guard_bash)")
    if ENV_OVERRIDE.search(cmd):
        deny("Blocked: overriding OUTREACH_* / CLAUDE_PROJECT_DIR inline would redirect the "
             "gates or the compose webhook. (outreach guard_bash)")
    if DATA_WRITE.search(cmd):
        deny("Blocked: data/ and state/ change only through scripts/log_update.py, "
             "record_approval.py and the other gate scripts, never by shell redirection, "
             "sed -i, rm or mv. (outreach guard_bash)")
    if not maintenance_mode() and re.search(r"(>>?|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b)[^|;&]*"
                                            r"(scripts[/\\]|\.claude[/\\]|references[/\\]guardrails)", low):
        deny("Blocked: gate scripts, .claude/ and guardrails.md are read-only to the agent. "
             "the operator can relaunch with OUTREACH_MAINTENANCE=1 to change them. (outreach guard_bash)")


if __name__ == "__main__":
    guard(main)
