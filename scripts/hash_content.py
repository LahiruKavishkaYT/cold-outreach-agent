#!/usr/bin/env python3
"""Compute or verify the approval hash of a draft.

Compute:  python3 scripts/hash_content.py <draft.json>
Verify:   python3 scripts/hash_content.py <draft.json> --expect <hash>

On --expect, exit 0 if the draft's current hash matches (approval still valid),
exit 2 if it differs (content changed -> approval void, return to review).
"""
import sys
from _common import load_draft, content_hash

def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit("usage: hash_content.py <draft.json> [--expect <hash>]")
    draft = load_draft(args[0])
    h = content_hash(draft)
    if "--expect" in args:
        expected = args[args.index("--expect") + 1].strip()
        if h == expected:
            print("PASS hash_content: matches approved hash {}".format(h[:12]))
        else:
            print("FAIL hash_content: content changed since approval")
            print("  approved: {}".format(expected[:12]))
            print("  current:  {}".format(h[:12]))
            sys.exit(2)
    else:
        print(h)

if __name__ == "__main__":
    main()
