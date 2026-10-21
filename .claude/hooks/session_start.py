#!/usr/bin/env python3
"""SessionStart: reconcile state and brief Claude on the pipeline.

Replaces the v2 "session start ritual" (which relied on the model remembering
to run sync_state.py). Runs sync_state.py, then injects a short factual
summary: counts per state, leads needing the operator, follow-ups that are due,
expiring approvals, approval-log integrity, and setup gaps.
"""
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from hooklib import read_input, use_project_scripts, add_context

FOLLOWUP_DAYS = {1: 4, 2: 7, 3: 7}  # F1 +3-4d, F2 +5-7d, F3 +7d (email-craft.md)


def parse(ts):
    """ISO timestamp or bare date -> aware UTC datetime (None if unparseable)."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.fromisoformat(str(ts)[:10])
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main():
    inp = read_input()
    sdir = use_project_scripts(inp)
    if not sdir:
        return
    import _common as c  # noqa: E402 (path set above)

    py = sys.executable
    subprocess.run([py, os.path.join(sdir, "sync_state.py")], capture_output=True, timeout=60)
    ver = subprocess.run([py, os.path.join(sdir, "verify_approvals.py")], capture_output=True,
                         text=True, timeout=30).stdout.strip()

    idx = c.load_index()
    counts = Counter(r.get("state") for r in idx.values())
    now = datetime.now(timezone.utc)
    needs = {"awaiting_final_approval": [], "changes_requested": [], "blocked": [], "expired": []}
    due, expiring, stale = [], [], []
    for lid, r in sorted(idx.items()):
        st = r.get("state")
        if st in needs:
            needs[st].append(lid)
        if st == "sent_by_user" and r.get("outcome") is None:
            sent = parse(r.get("sent_date"))
            n = int(r.get("followups_sent", 0) or 0) + 1
            if sent and now - sent > timedelta(days=30):
                stale.append(lid)  # sequence window passed; rests 90 days per email-craft.md
            elif sent and n <= 3 and now - sent >= timedelta(days=FOLLOWUP_DAYS[n]):
                due.append("{} (F{})".format(lid, n))
        if st in ("approved_for_draft", "saved_as_draft"):
            d = c.load_json(os.path.join(c.STATE, "draft", lid + ".json"), {}) or {}
            exp = d.get("approval_expiry_date")
            if exp and exp <= (now + timedelta(days=2)).date().isoformat():
                expiring.append("{} ({})".format(lid, exp))

    setup = []
    canon = c.canonical_numbers_by_vertical()
    for v in c.VERTICALS:
        if not canon.get(v):
            setup.append("no canonical demo number in references/positioning-{}.md (drafts for {} must be number-free)".format(v, v))
    if not os.environ.get("OUTREACH_COMPOSE_WEBHOOK"):
        setup.append("OUTREACH_COMPOSE_WEBHOOK unset: approved drafts are saved locally under data/drafts/approved/")
    prof = os.path.join(c.REFERENCES, "sender-profile.md")
    if not os.path.exists(prof) or "[[MISSING" in open(prof, encoding="utf-8").read():
        setup.append("references/sender-profile.md has no postal address (CAN-SPAM footer)")

    lines = ["Outreach pipeline at session start ({} leads): {}".format(
        len(idx), ", ".join("{} {}".format(v, k) for k, v in counts.most_common()) or "empty")]
    for k, v in needs.items():
        if v:
            lines.append("- {} ({}): {}".format(k, len(v), ", ".join(v[:12]) + (" ..." if len(v) > 12 else "")))
    if due:
        lines.append("- follow-ups due ({}): {}".format(len(due), ", ".join(due[:12]) + (" ..." if len(due) > 12 else "")))
    if stale:
        lines.append("- sent >30 days ago with no logged reply ({}): sequence window passed; log any replies with /reply, else they rest 90 days".format(len(stale)))
    if expiring:
        lines.append("- approvals expiring within 2 days: " + ", ".join(expiring))
    lines.append("- approvals log: " + (ver or "unknown"))
    for s in setup:
        lines.append("- setup: " + s)
    lines.append("Report anything needing the operator before taking new work. Dashboard: outputs/dashboard.html")
    add_context("\n".join(lines), "SessionStart")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("session_start hook error: {}".format(e), file=sys.stderr)
        sys.exit(0)
