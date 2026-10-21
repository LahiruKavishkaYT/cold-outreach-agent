#!/usr/bin/env python3
"""Single command for ALL lead state transitions. Auto-tracking spine.

Usage:
  python3 scripts/log_update.py set <lead-id> <state> [k=v ...]
  python3 scripts/log_update.py sent <lead-id> [<lead-id> ...]
  python3 scripts/log_update.py outcome <lead-id> <positive|negative|neutral|bounce|optout> ["note"]
  python3 scripts/log_update.py suppress <email|@domain> ["reason"]

Every call updates state/leads-index.json, stamps updated_at, and rebuilds
outputs/dashboard.html.

v3 enforcement (all deterministic):
  - Transitions follow the state machine in approval-policy.md. Illegal jumps
    (e.g. drafting -> sent_by_user) are refused.
  - approved_for_draft is refused unless the lead's draft carries an
    approved_hash that is present in data/approvals.log (i.e. it went through
    record_approval.py).
  - `sent` is refused unless the operator said something about sending/scheduling in
    a prompt they typed in the last 12 hours (operator log). The model cannot
    mark mail sent on its own.

Common k=v fields: vertical=dealers|medspa, campaign_id=..., recipient=...,
company=..., website=..., batch_id=..., email_version=N, touch=first|followup|reply,
message_version=..., note="..."
"""
import os
import re
import subprocess
import sys
from _common import (load_json, write_json_atomic, OUTREACH_LOG, SUPPRESSION_FILE,
                     APPROVALS_LOG, STATE, INDEX, normalize_email, iso_now,
                     operator_entries, load_index, valid_email)

VALID_STATES = {
    "researching", "researched", "research_blocked", "no_email", "skipped_has_chat",
    "drafting", "awaiting_review", "blocked", "changes_requested", "revised",
    "awaiting_final_approval", "approved_for_draft", "saved_as_draft",
    "ready_for_manual_send", "sent_by_user", "reply_received", "cancelled", "expired",
}
PRE_SEND = {"researching", "researched", "drafting", "awaiting_review", "blocked",
            "changes_requested", "revised", "awaiting_final_approval",
            "approved_for_draft", "saved_as_draft", "ready_for_manual_send", "expired"}
ALLOWED = {
    None: {"researching", "researched", "drafting", "no_email", "research_blocked", "skipped_has_chat"},
    "researching": {"researched", "research_blocked", "no_email", "skipped_has_chat", "drafting"},
    "researched": {"drafting", "researching", "no_email", "skipped_has_chat"},
    "research_blocked": {"researching", "researched"},
    "no_email": {"researching"},
    "skipped_has_chat": {"researching"},
    "drafting": {"awaiting_review", "awaiting_final_approval", "blocked"},
    "awaiting_review": {"awaiting_final_approval", "changes_requested", "blocked", "drafting"},
    "blocked": {"drafting", "revised", "changes_requested", "awaiting_review"},
    "changes_requested": {"revised", "drafting", "blocked"},
    "revised": {"awaiting_review", "awaiting_final_approval", "blocked", "changes_requested"},
    "awaiting_final_approval": {"approved_for_draft", "changes_requested", "blocked", "revised"},
    "approved_for_draft": {"saved_as_draft", "changes_requested", "expired"},
    "saved_as_draft": {"ready_for_manual_send", "changes_requested", "expired"},
    "ready_for_manual_send": {"changes_requested", "expired"},
    "expired": {"drafting", "revised", "awaiting_final_approval", "changes_requested"},
    "sent_by_user": {"reply_received", "drafting"},       # drafting = next follow-up
    "reply_received": {"drafting"},
    "cancelled": {"researching"},
}
SENT_WORDS = re.compile(r"\b(sent|send|sended|scheduled|schedule)\b", re.I)


def rebuild_dashboard():
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(here, "build_dashboard.py")], capture_output=True)


def save_index(idx):
    write_json_atomic(INDEX, idx, indent=1, sort_keys=True)


def draft_is_logged_approved(lead):
    d = load_json(os.path.join(STATE, "draft", "{}.json".format(lead)), {}) or {}
    h = d.get("approved_hash")
    if not h:
        return False
    try:
        return h in open(APPROVALS_LOG, encoding="utf-8").read()
    except FileNotFoundError:
        return False


def set_state(lead, state, kv):
    if state not in VALID_STATES:
        raise SystemExit("FAIL: unknown state '{}'".format(state))
    if state == "sent_by_user":
        raise SystemExit("FAIL: use `log_update.py sent <lead-id>` after the operator confirms a manual send")
    idx = load_index()
    rec = idx.get(lead, {"lead_id": lead, "created_at": iso_now(), "history": []})
    prev = rec.get("state")
    if state == "cancelled":
        if prev not in PRE_SEND | {None, "reply_received", "sent_by_user"}:
            raise SystemExit("FAIL: cannot cancel from '{}'".format(prev))
    elif prev != state and state not in ALLOWED.get(prev, set()):
        raise SystemExit("FAIL: illegal transition {} -> {} (allowed: {})".format(
            prev, state, ", ".join(sorted(ALLOWED.get(prev, set()))) or "none"))
    if state == "approved_for_draft" and not draft_is_logged_approved(lead):
        raise SystemExit("FAIL: {} has no logged approval. Run record_approval.py with "
                         "the operator's exact words first.".format(lead))
    for pair in kv:
        if "=" in pair:
            k, v = pair.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in ("state", "history", "sent_date"):
                continue
            if k == "recipient":
                v = normalize_email(v)
            rec[k] = v
    rec["state"] = state
    rec["updated_at"] = iso_now()
    rec.setdefault("history", []).append({"at": iso_now(), "from": prev, "to": state})
    idx[lead] = rec
    save_index(idx)
    rebuild_dashboard()
    print("OK {}: {} -> {}".format(lead, prev, state))


def operator_confirmed_send():
    return any(SENT_WORDS.search(e.get("text", "")) for e in operator_entries(12 * 60))


def mark_sent(leads):
    if not operator_confirmed_send():
        raise SystemExit("FAIL: no send confirmation from the operator in the last 12h. Only mark "
                         "sent after they says they sent/scheduled it themselves.")
    idx = load_index()
    log = load_json(OUTREACH_LOG, []) or []
    for lead in leads:
        rec = idx.get(lead)
        if not rec:
            print("FAIL: unknown lead '{}'".format(lead))
            continue
        if rec.get("state") not in ("saved_as_draft", "ready_for_manual_send", "approved_for_draft"):
            print("FAIL {}: state is '{}'; only approved/saved drafts can be marked sent".format(
                lead, rec.get("state")))
            continue
        ts = iso_now()
        prev = rec.get("state")
        rec.update({"state": "sent_by_user", "sent_date": ts, "updated_at": ts})
        if rec.get("touch") == "followup":
            rec["followups_sent"] = int(rec.get("followups_sent", 0) or 0) + 1
        rec.setdefault("history", []).append({"at": ts, "from": prev, "to": "sent_by_user"})
        log.append({"lead_id": lead, "recipient": rec.get("recipient", ""),
                    "campaign_id": rec.get("campaign_id", ""), "vertical": rec.get("vertical", ""),
                    "email_version": rec.get("email_version", ""),
                    "touch": rec.get("touch", "first"),
                    "message_version": rec.get("message_version", ""),
                    "status": "sent_by_user", "sent_date": ts})
        print("OK {}: sent_by_user @ {} (dedup log updated)".format(lead, ts))
    save_index(idx)
    write_json_atomic(OUTREACH_LOG, log, indent=1)
    rebuild_dashboard()


def append_suppression(addr, reason):
    addr = normalize_email(addr)
    if not (addr.startswith("@") or valid_email(addr)):
        raise SystemExit("FAIL: not an email or @domain: {}".format(addr))
    with open(SUPPRESSION_FILE, "a", encoding="utf-8") as fh:
        fh.write("{}  # {} {}\n".format(addr, reason, iso_now()[:10]))
    print("OK suppressed {}".format(addr))


def outcome(lead, kind, note):
    kinds = {"positive", "negative", "neutral", "bounce", "optout"}
    if kind not in kinds:
        raise SystemExit("FAIL: outcome must be one of {}".format(sorted(kinds)))
    idx = load_index()
    rec = idx.get(lead)
    if not rec:
        raise SystemExit("FAIL: unknown lead '{}'".format(lead))
    ts = iso_now()
    prev = rec.get("state")
    rec["state"] = "reply_received" if kind in ("positive", "negative", "neutral") else prev
    rec["outcome"] = kind
    if note:
        rec["outcome_note"] = note
    if kind in ("optout", "negative"):
        addr = rec.get("recipient", "")
        if addr:
            append_suppression(addr, "{} ({})".format(kind, lead))
        if kind == "optout":
            rec["state"] = "cancelled"
    if kind == "bounce":
        rec["state"] = "cancelled"
    rec["updated_at"] = ts
    rec.setdefault("history", []).append({"at": ts, "from": prev, "to": "outcome:{}".format(kind)})
    idx[lead] = rec
    save_index(idx)
    rebuild_dashboard()
    print("OK {}: outcome={} state={}".format(lead, kind, rec["state"]))


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    cmd = a[0]
    if cmd == "set" and len(a) >= 3:
        set_state(a[1], a[2], a[3:])
    elif cmd == "sent" and len(a) >= 2:
        mark_sent(a[1:])
    elif cmd == "outcome" and len(a) >= 3:
        outcome(a[1], a[2], a[3] if len(a) > 3 else "")
    elif cmd == "suppress" and len(a) >= 2:
        append_suppression(a[1], a[2] if len(a) > 2 else "manual")
        rebuild_dashboard()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
