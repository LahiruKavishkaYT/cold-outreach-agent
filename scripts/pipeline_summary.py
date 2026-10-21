#!/usr/bin/env python3
"""Compact pipeline snapshot for skills (dynamic context) and humans.

Usage: python3 scripts/pipeline_summary.py [--metrics]

Default: counts per state + leads needing the operator.
--metrics: per campaign / vertical / message_version reply metrics from the
outreach log and index outcomes. Refuses conclusions under 30 sends.
"""
import sys
from collections import Counter, defaultdict
from _common import load_index, load_json, OUTREACH_LOG

ACTION = ("awaiting_final_approval", "changes_requested", "blocked", "expired")


def main():
    idx = load_index()
    c = Counter(r.get("state") for r in idx.values())
    print("leads: {} | {}".format(len(idx), ", ".join("{} {}".format(v, k) for k, v in c.most_common()) or "none"))
    for st in ACTION:
        ids = sorted(l for l, r in idx.items() if r.get("state") == st)
        if ids:
            print("{} ({}): {}".format(st, len(ids), ", ".join(ids[:15]) + (" ..." if len(ids) > 15 else "")))
    if "--metrics" not in sys.argv:
        return
    log = load_json(OUTREACH_LOG, []) or []
    groups = defaultdict(lambda: {"sent": 0, "replies": 0, "positive": 0, "optout": 0, "bounce": 0})
    for e in log:
        if e.get("status") != "sent_by_user":
            continue
        rec = idx.get(e.get("lead_id"), {})
        key = (e.get("vertical") or rec.get("vertical") or "?", e.get("campaign_id") or "?",
               e.get("message_version") or rec.get("message_version") or "-")
        g = groups[key]
        g["sent"] += 1
        oc = rec.get("outcome")
        if oc in ("positive", "neutral", "negative", "optout"):
            g["replies"] += 1
        if oc == "positive":
            g["positive"] += 1
        if oc in ("optout", "bounce"):
            g[oc] += 1
    print("\nvertical | campaign | message_version | sent | replies | reply% | positive | optout | bounce")
    for (v, cid, mv), g in sorted(groups.items()):
        rate = 100.0 * g["replies"] / g["sent"] if g["sent"] else 0
        flag = "" if g["sent"] >= 30 else "  (n<30: no conclusions)"
        print("{} | {} | {} | {} | {} | {:.1f}% | {} | {} | {}{}".format(
            v, cid, mv, g["sent"], g["replies"], rate, g["positive"], g["optout"], g["bounce"], flag))


if __name__ == "__main__":
    main()
