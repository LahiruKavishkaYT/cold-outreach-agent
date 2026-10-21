#!/usr/bin/env python3
"""Hard gate: fail if a draft still contains unfilled placeholders.

Usage: python3 scripts/placeholder_scan.py <draft.json>
Exit 0 = clean. Exit 2 = placeholders found (block).
"""
import sys
from _common import load_draft, PLACEHOLDER_PATTERNS

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: placeholder_scan.py <draft.json>")
    draft = load_draft(sys.argv[1])
    haystack = "\n".join(str(draft.get(f, "")) for f in ("subject", "body"))
    hits = []
    for pat in PLACEHOLDER_PATTERNS:
        for m in pat.findall(haystack):
            hits.append(m if isinstance(m, str) else str(m))
    if hits:
        print("FAIL placeholder_scan: unresolved placeholders -> " + ", ".join(sorted(set(hits))))
        sys.exit(2)
    print("PASS placeholder_scan")

if __name__ == "__main__":
    main()
