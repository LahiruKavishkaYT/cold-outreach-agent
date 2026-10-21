#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit|NotebookEdit) guard.

Protects the trust anchors and the state machine from direct file edits:
  - data/approvals.log, data/.operator/**      never writable by the agent
  - data/outreach-log.json, data/suppression.txt, state/leads-index.json
                                               only via scripts/log_update.py
  - approval fields inside state/draft/*.json  only via scripts/record_approval.py
  - .claude/** and scripts/**                  read-only unless Claude Code was
                                               launched with OUTREACH_MAINTENANCE=1
"""
import json
import os
import re
from hooklib import read_input, deny, guard, project_dir, rel, maintenance_mode

APPROVAL_FIELDS = ("approved_hash", "approved_date", "approval_expiry_date", "approval_text")
NEVER = (re.compile(r"^data/approvals\.log$"), re.compile(r"^data/\.operator(/|$)"))
VIA_SCRIPTS = {
    "data/outreach-log.json": "log_update.py sent",
    "data/suppression.txt": "log_update.py suppress <email|@domain> \"reason\"",
    "state/leads-index.json": "log_update.py set <lead> <state>",
}


def approval_changed(old, new):
    for f in APPROVAL_FIELDS:
        if (new or {}).get(f) and (new or {}).get(f) != (old or {}).get(f):
            return f
    st = (new or {}).get("approval_status")
    if st in ("approved_for_draft", "saved_as_draft", "sent_by_user") and st != (old or {}).get("approval_status"):
        return "approval_status"
    return None


def main():
    inp = read_input()
    ti = inp.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    root = project_dir(inp)
    r = rel(path, root)
    if not r:
        return  # outside the project: normal permissions apply

    for rx in NEVER:
        if rx.search(r):
            deny("Blocked: {} is append-only evidence written by scripts/hooks only. "
                 "(outreach guard_files)".format(r))
    if r in VIA_SCRIPTS:
        deny("Blocked: {} changes only through `python3 scripts/{}` so every change is "
             "validated and logged. (outreach guard_files)".format(r, VIA_SCRIPTS[r]))
    if not maintenance_mode() and (r.startswith(".claude/") or r.startswith("scripts/")
                                   or r == "references/guardrails.md"):
        deny("Blocked: {} is part of the enforcement layer and read-only to the agent. "
             "the operator can relaunch with OUTREACH_MAINTENANCE=1 to edit it. (outreach guard_files)".format(r))

    if re.match(r"^state/draft/[^/]+\.json$", r) or re.match(r"^data/drafts/", r):
        full = os.path.join(root, r)
        try:
            old = json.load(open(full, encoding="utf-8"))
        except Exception:
            old = {}
        tool = inp.get("tool_name")
        if tool == "Write":
            try:
                new = json.loads(ti.get("content") or "{}")
            except json.JSONDecodeError:
                deny("Blocked: draft content is not valid JSON. (outreach guard_files)")
            f = approval_changed(old, new)
            if f:
                deny("Blocked: `{}` is set only by scripts/record_approval.py from the operator's own "
                     "words. Write the draft without approval fields. (outreach guard_files)".format(f))
            if old.get("approved_hash") and any(new.get(k) != old.get(k) for k in
                                                ("subject", "body", "recipient", "cc", "bcc")) \
                    and new.get("email_version") == old.get("email_version"):
                deny("Blocked: this draft version was approved; changing it in place would "
                     "silently alter an approved email. Write a NEW email_version (and drop the "
                     "approval fields). (outreach guard_files)")
        else:
            blob = json.dumps(ti)
            if any(f in blob for f in APPROVAL_FIELDS) or re.search(
                    r'approval_status\\?"\s*:\s*\\?"(approved_for_draft|saved_as_draft|sent_by_user)', blob):
                deny("Blocked: approval fields are set only by scripts/record_approval.py. "
                     "(outreach guard_files)")
            if old.get("approved_hash"):
                deny("Blocked: this draft version was approved; edit by writing a NEW "
                     "email_version instead of editing it in place. (outreach guard_files)")


if __name__ == "__main__":
    guard(main)
