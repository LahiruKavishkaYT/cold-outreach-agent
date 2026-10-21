#!/usr/bin/env python3
"""Reconcile state/leads-index.json against data/drafts/* folders.

Usage: python3 scripts/sync_state.py

- Registers any draft found in data/drafts/{approved,sent,awaiting-review}/ that
  is missing from the index, deriving state from the folder.
- Applies the 7-day approval expiry: approved drafts past approval_expiry_date
  move to 'expired' (re-validate before use).
- Never deletes or downgrades a sent/replied state. Rebuilds the dashboard.
"""
import glob, json, os, subprocess, sys
from datetime import datetime, timezone
from _common import load_json, ROOT, INDEX, write_json_atomic, infer_vertical_from_campaign
FOLDER_STATE = {"approved": "approved_for_draft", "sent": "sent_by_user",
                "awaiting-review": "awaiting_final_approval"}

def main():
    idx = load_json(INDEX, {}) or {}
    today = datetime.now(timezone.utc).date().isoformat()
    added, expired = 0, 0
    for folder, state in FOLDER_STATE.items():
        for path in glob.glob(os.path.join(ROOT, "data", "drafts", folder, "*.json")):
            d = load_json(path)
            if not d: continue
            lid = d.get("lead_id") or os.path.basename(path).split("_v")[0]
            rec = idx.get(lid, {"lead_id": lid, "history": []})
            cur = rec.get("state")
            if cur in ("sent_by_user", "reply_received"):
                pass  # never downgrade
            elif cur != state:
                rec["state"] = state
                rec.setdefault("history", []).append(
                    {"at": datetime.now(timezone.utc).isoformat(), "to": state, "via": "sync"})
                added += 1
            rec.setdefault("recipient", d.get("recipient", ""))
            rec.setdefault("company", d.get("company_name", ""))
            rec.setdefault("campaign_id", d.get("campaign_id", ""))
            rec.setdefault("email_version", d.get("email_version", ""))
            if not rec.get("vertical"):
                v = d.get("vertical") or infer_vertical_from_campaign(d.get("campaign_id"))
                if v: rec["vertical"] = v
            exp = d.get("approval_expiry_date")
            if rec["state"] in ("approved_for_draft", "saved_as_draft", "ready_for_manual_send") and exp and exp < today:
                rec["state"] = "expired"; expired += 1
                rec["history"].append({"at": datetime.now(timezone.utc).isoformat(),
                                       "to": "expired", "via": "sync (approval_expiry_date {})".format(exp)})
            rec["updated_at"] = datetime.now(timezone.utc).isoformat()
            idx[lid] = rec
    write_json_atomic(INDEX, idx, indent=1, sort_keys=True)
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(here, "build_dashboard.py")], capture_output=True)
    print("sync: {} leads in index, {} state changes, {} expired".format(len(idx), added, expired))

if __name__ == "__main__":
    main()
