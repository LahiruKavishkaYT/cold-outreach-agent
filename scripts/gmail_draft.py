#!/usr/bin/env python3
"""Create a Gmail DRAFT from an approved message. Compose only. Never sends.

This script does exactly one external thing: hand an already-approved draft to
an n8n webhook whose workflow uses gmail.compose to create a draft. There is no
send action anywhere in this file, by design.

Hard preconditions (all enforced here, not just by prompt):
  1. The draft must already carry an `approved_hash`.
  2. The draft's current content hash must equal `approved_hash` (no drift).
  3. precheck must pass (re-run here as a backstop).
If any fails, the script refuses and exits non-zero.

Webhook URL comes from the env var OUTREACH_COMPOSE_WEBHOOK. If it is unset,
the script falls back to writing a local draft file under
data/drafts/approved/ and prints a clear notice. Everything else still works.

Usage:
  python3 scripts/gmail_draft.py <draft.json>

The script never reads or stores secrets in files. The webhook URL is read from
the environment only.
"""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from _common import load_draft, content_hash, ROOT, DATA, APPROVALS_LOG

WEBHOOK_ENV = "OUTREACH_COMPOSE_WEBHOOK"
HERE = os.path.dirname(os.path.abspath(__file__))


def refuse(msg):
    print("REFUSED: " + msg)
    sys.exit(2)


def backstop_precheck(path):
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "precheck.py"), path],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        refuse("precheck did not pass at draft-creation time.")


def post_compose(url, payload):
    """POST the draft to the n8n compose webhook. Expects the workflow to use
    gmail.compose and return JSON with a draft id. We never send."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "replace")
        return resp.status, body


def local_fallback(draft):
    out_dir = os.path.join(DATA, "drafts", "approved")
    os.makedirs(out_dir, exist_ok=True)
    fname = "{}_v{}.json".format(draft.get("lead_id", "lead"), draft.get("email_version", "1"))
    path = os.path.join(out_dir, fname)
    draft = dict(draft)
    draft["compose_status"] = "local_only_webhook_unset"
    draft["compose_attempted_at"] = datetime.now(timezone.utc).isoformat()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(draft, fh, indent=2)
    return path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: gmail_draft.py <draft.json>")
    path = sys.argv[1]
    draft = load_draft(path)

    approved = draft.get("approved_hash")
    if not approved:
        refuse("draft has no approved_hash. It was never explicitly approved.")
    current = content_hash(draft)
    if current != approved:
        refuse("content changed since approval (hash mismatch). Return to review.")
    # v3: the hash must also be in the append-only approvals log (written only
    # by record_approval.py), so a hand-typed approved_hash can't pass.
    try:
        logged = approved in open(APPROVALS_LOG, encoding="utf-8").read()
    except FileNotFoundError:
        logged = False
    if not logged:
        refuse("approved_hash is not in data/approvals.log. Run record_approval.py.")
    exp = draft.get("approval_expiry_date")
    if exp and exp < datetime.now(timezone.utc).date().isoformat():
        refuse("approval expired on {}. Re-validate and re-approve.".format(exp))

    backstop_precheck(path)

    payload = {
        "intent": "create_draft_only",
        "recipient": draft.get("recipient"),
        "cc": draft.get("cc", []),
        "bcc": draft.get("bcc", []),
        "subject": draft.get("subject"),
        "body": draft.get("body"),
        "lead_id": draft.get("lead_id"),
        "campaign_id": draft.get("campaign_id"),
        "email_version": draft.get("email_version"),
        "approved_hash": approved,
    }

    url = os.environ.get(WEBHOOK_ENV, "").strip()
    if not url:
        p = local_fallback(draft)
        print("NOTE: {} not set. Wrote local draft instead: {}".format(WEBHOOK_ENV, p))
        print("      Wire the n8n compose webhook and re-run to create a Gmail draft.")
        return

    try:
        status, body = post_compose(url, payload)
    except urllib.error.URLError as e:
        p = local_fallback(draft)
        print("WARN: webhook call failed ({}). Wrote local draft: {}".format(e, p))
        sys.exit(1)

    if 200 <= status < 300:
        print("OK: Gmail draft created via compose webhook (status {}).".format(status))
        print(body[:500])
    else:
        p = local_fallback(draft)
        print("WARN: webhook returned status {}. Wrote local draft: {}".format(status, p))
        sys.exit(1)


if __name__ == "__main__":
    main()
