#!/usr/bin/env python3
"""ADVISORY gate: inspect links for format problems. Never blocks on network.

Reachability is intentionally NOT tested here -- a transient timeout must never
block a good draft. We flag malformed URLs, placeholder/example domains, and
bare 'http' fragments as warnings. Exit is always 0; warnings go to stdout with
a WARN prefix so the critic can surface them.

Usage: python3 scripts/link_check.py <draft.json>
"""
import re
import sys
from _common import load_draft

URL = re.compile(r"https?://[^\s)\]>\"']+", re.IGNORECASE)
BAD_HOSTS = ("example.com", "example.org", "yourdomain", "lvh.me", "localhost", "test.test")

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: link_check.py <draft.json>")
    draft = load_draft(sys.argv[1])
    body = "{}\n{}".format(draft.get("subject", ""), draft.get("body", ""))
    warns = []
    urls = URL.findall(body)
    for u in urls:
        low = u.lower()
        if any(h in low for h in BAD_HOSTS):
            warns.append("placeholder/example domain: {}".format(u))
        if low.count("://") > 1:
            warns.append("malformed (double scheme): {}".format(u))
    # bare 'http' with no host
    for frag in re.findall(r"https?://(?=\s|$)", body):
        warns.append("empty link: {}".format(frag))
    if warns:
        for w in warns:
            print("WARN link_check: " + w)
    else:
        print("PASS link_check: {} link(s), no format issues".format(len(urls)))

if __name__ == "__main__":
    main()
