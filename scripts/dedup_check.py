#!/usr/bin/env python3
"""Hard gate: block a duplicate send to the same address within a window.

Usage: python3 scripts/dedup_check.py <recipient_email> [window_days=14]
Counts only log entries with status sent_by_user. Exit 2 = duplicate (block).
"""
import sys
from datetime import datetime, timezone, timedelta
from _common import load_json, OUTREACH_LOG, normalize_email

def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: dedup_check.py <recipient_email> [window_days]")
    addr = normalize_email(sys.argv[1])
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    cutoff = datetime.now(timezone.utc) - timedelta(days=window)
    log = load_json(OUTREACH_LOG, []) or []
    for entry in log:
        if normalize_email(entry.get("recipient")) != addr:
            continue
        if entry.get("status") != "sent_by_user":
            continue
        sent = entry.get("sent_date")
        if not sent:
            continue
        try:
            when = datetime.fromisoformat(sent.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when >= cutoff:
            print("FAIL dedup_check: {} contacted on {} (within {}d)".format(addr, sent, window))
            sys.exit(2)
    print("PASS dedup_check: no send to {} within {}d".format(addr, window))

if __name__ == "__main__":
    main()
