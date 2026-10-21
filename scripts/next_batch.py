#!/usr/bin/env python3
"""Pick the next batch of unprocessed leads from a CSV. Deterministic.

Usage: python3 scripts/next_batch.py <inputs/leads.csv> [--size 10] [--vertical dealers|medspa] [--campaign ID]

Filters out, in order: rows without a usable email, suppressed addresses,
addresses already sent within 14d (dedup log), and leads already present in
state/leads-index.json in any non-terminal state. Prints the batch and writes a
manifest to state/batches/<batch-id>.json for the skills to work from.

CSV columns recognized (case-insensitive, flexible): company/name/business,
email OR "contact info", website/domain/url, vertical, and a "1st reach"-style
column — any row with that filled is treated as already contacted and skipped
(your manual CSV history is honored; going forward the index tracks it).
"""
import csv, json, os, re, sys
from datetime import datetime, timezone, timedelta
from _common import load_json, load_suppression, is_suppressed, normalize_email, OUTREACH_LOG, ROOT, valid_email

INDEX = os.path.join(ROOT, "state", "leads-index.json")
BATCH_DIR = os.path.join(ROOT, "state", "batches")
TERMINAL = {"cancelled", "expired", "no_email", "research_blocked", "skipped_has_chat"}

def slug(s):
    s = re.sub(r"https?://(www\.)?", "", (s or "").lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "lead"

def pick_col(headers, *cands):
    lower = {h.lower().strip(): h for h in headers}
    for c in cands:
        for k, orig in lower.items():
            if c in k:
                return orig
    return None

def recent_sends(window_days=14):
    out = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    for e in (load_json(OUTREACH_LOG, []) or []):
        if e.get("status") != "sent_by_user":
            continue
        try:
            when = datetime.fromisoformat(str(e.get("sent_date","")).replace("Z","+00:00"))
        except ValueError:
            continue
        if when >= cutoff:
            out.add(normalize_email(e.get("recipient")))
    return out

def main():
    args = sys.argv[1:]
    if not args: raise SystemExit(__doc__)
    csv_path = args[0]
    size = int(args[args.index("--size")+1]) if "--size" in args else 10
    vertical = args[args.index("--vertical")+1] if "--vertical" in args else ""
    campaign = args[args.index("--campaign")+1] if "--campaign" in args else ""

    idx = load_json(INDEX, {}) or {}
    suppressed = load_suppression()
    sent = recent_sends()
    known_emails = {normalize_email(r.get("recipient")) for r in idx.values() if r.get("recipient")}
    active_ids = {lid for lid, r in idx.items() if r.get("state") not in TERMINAL}

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows: raise SystemExit("FAIL: empty CSV")
    headers = rows[0].keys()
    c_email = pick_col(headers, "email", "contact info", "contact")
    c_co    = pick_col(headers, "company", "business", "name")
    c_web   = pick_col(headers, "website", "domain", "url")
    c_vert  = pick_col(headers, "vertical")
    c_reach = pick_col(headers, "1st reach", "first reach", "reached", "sent")
    if not c_email: raise SystemExit("FAIL: no email column found in {}".format(list(headers)))

    batch, skipped = [], {"no_email":0,"suppressed":0,"dedup_14d":0,"already_in_pipeline":0,"csv_marked_contacted":0}
    for r in rows:
        if len(batch) >= size: break
        email = normalize_email(r.get(c_email, ""))
        if not valid_email(email): skipped["no_email"] += 1; continue
        if c_reach and (r.get(c_reach) or "").strip(): skipped["csv_marked_contacted"] += 1; continue
        if is_suppressed(email): skipped["suppressed"] += 1; continue
        if email in sent: skipped["dedup_14d"] += 1; continue
        lid = slug(r.get(c_co) or r.get(c_web) or email.split("@")[1])
        if lid in active_ids or email in known_emails: skipped["already_in_pipeline"] += 1; continue
        batch.append({
            "lead_id": lid, "recipient": email,
            "company": (r.get(c_co) or "").strip(),
            "website": (r.get(c_web) or "").strip(),
            "vertical": (r.get(c_vert) or vertical or "").strip(),
            "row": r,
        })
        known_emails.add(email); active_ids.add(lid)

    missing_vert = [b["lead_id"] for b in batch if not b["vertical"]]
    batch_id = "batch-{}".format(datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    os.makedirs(BATCH_DIR, exist_ok=True)
    manifest = {"batch_id": batch_id, "source_csv": csv_path, "campaign_id": campaign,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "leads": batch, "skipped": skipped}
    path = os.path.join(BATCH_DIR, batch_id + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)

    print("BATCH {} — {} leads (manifest: {})".format(batch_id, len(batch), os.path.relpath(path, ROOT)))
    for b in batch:
        print("  {:<30} {:<32} vertical={}".format(b["lead_id"], b["recipient"], b["vertical"] or "?"))
    print("skipped:", json.dumps(skipped))
    if missing_vert:
        print("WARN: no vertical for: {} — pass --vertical or add a CSV column before drafting".format(", ".join(missing_vert)))
        sys.exit(3)

if __name__ == "__main__":
    main()
