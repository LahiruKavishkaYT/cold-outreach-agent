#!/usr/bin/env python3
"""Record the operator's explicit approval of one exact draft version. Append-only.

Usage:
  python3 scripts/record_approval.py <draft.json> --text "<the operator's exact words>"

Refuses (exit 2) unless ALL of these hold:
  1. The text is explicit approval language (approval-policy.md). "looks good",
     "continue", "sended", "nice" are not approval.
  2. The text appears verbatim inside a prompt the operator actually typed in this
     project within the last 3 hours. Those prompts are captured by the
     UserPromptSubmit hook into data/.operator/prompts.jsonl, a file the model
     cannot write (guard hooks). So approval cannot originate from a web page,
     a prospect reply, or the model itself.
  3. precheck passes (no approving a blocked draft).

On success it:
  - writes approved_hash, approved_date, approval_expiry_date (+7d),
    approval_status=approved_for_draft and approval_text INTO the draft JSON
    (so the model never hand-writes approved_hash), and
  - appends a hash-chained line to data/approvals.log:
    <iso_utc> | <lead_id> | v<version> | <hash> | <text> | chain=<sha256>
    Each chain value covers the previous one, so editing or deleting an old
    line breaks verification (scripts/verify_approvals.py).
"""
import hashlib
import os
import subprocess
import sys
from datetime import timedelta
from _common import (load_draft, content_hash, APPROVALS_LOG, APPROVAL_TTL_DAYS,
                     is_explicit_approval, operator_said, write_json_atomic, now_utc)

HERE = os.path.dirname(os.path.abspath(__file__))


def refuse(msg):
    print("REFUSED record_approval: " + msg)
    sys.exit(2)


def last_chain():
    try:
        with open(APPROVALS_LOG, "r", encoding="utf-8") as fh:
            lines = [l.rstrip("\n") for l in fh if l.strip()]
    except FileNotFoundError:
        return "genesis"
    for line in reversed(lines):
        if "| chain=" in line:
            return line.rsplit("| chain=", 1)[1].strip()
    # legacy log with no chain yet: anchor the chain to the whole legacy content
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def main():
    args = sys.argv[1:]
    if len(args) < 3 or "--text" not in args:
        raise SystemExit('usage: record_approval.py <draft.json> --text "<approval text>"')
    path = args[0]
    text = args[args.index("--text") + 1].strip().replace("\n", " ").replace("|", "/")
    draft = load_draft(path)

    if not is_explicit_approval(text):
        refuse('"{}" is not explicit approval. Ask the operator for one of: "Approve this '
               'exact draft", "Approve the batch", "Approve all except #3", '
               '"Create the Gmail draft".'.format(text))
    if not operator_said(text):
        refuse("that approval text was not found in anything the operator typed in the last "
               "3 hours. Approval must be their own words in this session, quoted exactly.")
    pc = subprocess.run([sys.executable, os.path.join(HERE, "precheck.py"), path],
                        capture_output=True, text=True)
    if pc.returncode != 0:
        print(pc.stdout)
        refuse("precheck is BLOCKED; a blocked draft cannot be approved.")

    h = content_hash(draft)
    now = now_utc()
    draft["approved_hash"] = h
    draft["approved_date"] = now.date().isoformat()
    draft["approval_expiry_date"] = (now + timedelta(days=APPROVAL_TTL_DAYS)).date().isoformat()
    draft["approval_status"] = "approved_for_draft"
    draft["approval_text"] = text
    write_json_atomic(path, draft)

    core = "{} | {} | v{} | {} | {}".format(
        now.isoformat(), draft.get("lead_id", "?"), draft.get("email_version", "?"), h, text)
    chain = hashlib.sha256((last_chain() + "\n" + core).encode("utf-8")).hexdigest()
    os.makedirs(os.path.dirname(APPROVALS_LOG), exist_ok=True)
    with open(APPROVALS_LOG, "a", encoding="utf-8") as fh:
        fh.write("{} | chain={}\n".format(core, chain))
    print("recorded approval: lead={} v{} hash={} expires={}".format(
        draft.get("lead_id", "?"), draft.get("email_version", "?"), h[:12],
        draft["approval_expiry_date"]))
    print(h)


if __name__ == "__main__":
    main()
