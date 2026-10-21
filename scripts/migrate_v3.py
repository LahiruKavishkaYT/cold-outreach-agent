#!/usr/bin/env python3
"""One-time v2 -> v3 state migration. Dry run by default.

Usage:
  python3 scripts/migrate_v3.py            # report only
  python3 scripts/migrate_v3.py --apply    # write (backs up state/ and data/ first)

What it fixes (found in the v2 data):
  1. Sends recorded only inside draft JSON (approval_status=sent_by_user /
     sent_date) never reached data/outreach-log.json, so dedup_check could not
     see them. They are backfilled into the outreach log.
  2. Leads that exist in state/draft/ but not in state/leads-index.json are
     registered, with a state derived from the draft.
  3. Drafts get an explicit `vertical` (not part of the approval hash, so no
     approval is invalidated). Inferred from campaign_id, then the leads index,
     then the research file / company name.
  4. The legacy state/leads-index.dealer-2026-06.json side index is folded in.
"""
import glob
import json
import os
import re
import shutil
import sys
from _common import (ROOT, STATE, DATA, OUTREACH_LOG, INDEX, load_json, write_json_atomic,
                     infer_vertical_from_campaign, normalize_email, iso_now)

MEDSPA_HINT = re.compile(r"spa|medi|aesthetic|skin|laser|derma|beauty|wellness|hydrafacial|botox|inject", re.I)
DEALER_HINT = re.compile(r"car|motor|auto|dealer|vehicle|benz|beemer|lot\b", re.I)


def guess_vertical(draft, research, idx_rec):
    v = draft.get("vertical") or idx_rec.get("vertical") or infer_vertical_from_campaign(draft.get("campaign_id"))
    if v:
        return v, "campaign/index"
    if research.get("med_spa_classification"):
        return "medspa", "research.med_spa_classification"
    name = " ".join(str(x) for x in (draft.get("company_name"), draft.get("lead_id"),
                                     research.get("business_name"), research.get("company_name")) if x)
    if MEDSPA_HINT.search(name):
        return "medspa", "name heuristic"
    if DEALER_HINT.search(name):
        return "dealers", "name heuristic"
    return "", "unknown"


def draft_state(d):
    st = d.get("approval_status")
    if st == "sent_by_user" or d.get("sent_date"):
        return "sent_by_user"
    if d.get("approved_hash"):
        return "approved_for_draft"
    return "awaiting_final_approval"


def main():
    apply = "--apply" in sys.argv
    idx = load_json(INDEX, {}) or {}
    log = load_json(OUTREACH_LOG, []) or []
    logged = {(normalize_email(e.get("recipient")), e.get("lead_id")) for e in log}
    side = load_json(os.path.join(STATE, "leads-index.dealer-2026-06.json"), {}) or {}
    report = {"drafts_vertical_added": [], "vertical_unknown": [], "index_added": [],
              "index_state_fixed": [], "sends_backfilled": [], "side_index_merged": []}
    draft_writes = {}

    for path in sorted(glob.glob(os.path.join(STATE, "draft", "*.json"))):
        d = load_json(path)
        if not isinstance(d, dict):
            continue
        lid = d.get("lead_id") or os.path.basename(path)[:-5]
        research = load_json(os.path.join(STATE, "research", lid + ".json"), {}) or {}
        rec = idx.get(lid, {})
        v, how = guess_vertical(d, research, rec)
        if v and not d.get("vertical"):
            d["vertical"] = v
            draft_writes[path] = d
            report["drafts_vertical_added"].append("{} -> {} ({})".format(lid, v, how))
        if not v:
            report["vertical_unknown"].append(lid)
        st = draft_state(d)
        if lid not in idx:
            idx[lid] = {"lead_id": lid, "created_at": d.get("created_date") or iso_now(),
                        "history": [{"at": iso_now(), "to": st, "via": "migrate_v3"}]}
            report["index_added"].append("{} ({})".format(lid, st))
        rec = idx[lid]
        if st == "sent_by_user" and rec.get("state") != "sent_by_user" and rec.get("state") != "reply_received":
            report["index_state_fixed"].append("{}: {} -> sent_by_user".format(lid, rec.get("state")))
            rec.setdefault("history", []).append({"at": iso_now(), "from": rec.get("state"),
                                                  "to": "sent_by_user", "via": "migrate_v3"})
            rec["state"] = "sent_by_user"
        rec.setdefault("state", st)
        for k_src, k_dst in (("recipient", "recipient"), ("company_name", "company"),
                             ("campaign_id", "campaign_id"), ("email_version", "email_version")):
            if d.get(k_src) and not rec.get(k_dst):
                rec[k_dst] = normalize_email(d[k_src]) if k_dst == "recipient" else d[k_src]
        if v and not rec.get("vertical"):
            rec["vertical"] = v
        if st == "sent_by_user":
            sent = d.get("sent_date") or d.get("scheduled_send_at") or d.get("approved_date")
            rec.setdefault("sent_date", sent)
            key = (normalize_email(d.get("recipient")), lid)
            if key not in logged and d.get("recipient"):
                log.append({"lead_id": lid, "recipient": normalize_email(d.get("recipient")),
                            "campaign_id": d.get("campaign_id", ""), "vertical": v,
                            "email_version": d.get("email_version", ""), "touch": "first",
                            "status": "sent_by_user", "sent_date": sent, "source": "migrate_v3"})
                logged.add(key)
                report["sends_backfilled"].append("{} <{}> {}".format(lid, d.get("recipient"), sent))

    for lid, r in (side.get("leads") or {}).items():
        if lid in idx:
            continue
        st = r.get("state")
        st = {"scheduled": "sent_by_user"}.get(st, st)
        idx[lid] = {"lead_id": lid, "state": st, "recipient": normalize_email(r.get("recipient")),
                    "company": r.get("company_name", ""), "vertical": "dealers",
                    "campaign_id": side.get("campaign_id", ""), "note": r.get("note", ""),
                    "history": [{"at": iso_now(), "to": st, "via": "migrate_v3 side-index"}]}
        report["side_index_merged"].append("{} ({})".format(lid, st))

    for k, items in report.items():
        print("{:<24} {}".format(k, len(items)))
        for it in items[:60]:
            print("   - " + it)
    if not apply:
        print("\nDRY RUN. Re-run with --apply to write (a backup is taken first).")
        return
    stamp = iso_now()[:19].replace(":", "")
    bdir = os.path.join(ROOT, "backups", "pre-v3-" + stamp)
    shutil.copytree(STATE, os.path.join(bdir, "state"))
    shutil.copytree(DATA, os.path.join(bdir, "data"))
    for path, d in draft_writes.items():
        write_json_atomic(path, d)
    write_json_atomic(INDEX, idx, indent=1, sort_keys=True)
    write_json_atomic(OUTREACH_LOG, log, indent=1)
    print("\nAPPLIED. Backup: {}".format(os.path.relpath(bdir, ROOT)))


if __name__ == "__main__":
    main()
