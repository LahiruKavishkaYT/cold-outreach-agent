#!/usr/bin/env python3
"""Verify the append-only approvals log has not been edited.

Usage: python3 scripts/verify_approvals.py

Legacy v2 lines (no chain= field) are counted but can't be verified; the first
chained line anchors to a hash of all legacy content before it, so even
legacy lines are protected once one v3 approval exists.
Exit 0 = intact. Exit 2 = tampering detected.
"""
import hashlib
import sys
from _common import APPROVALS_LOG


def main():
    try:
        lines = [l.rstrip("\n") for l in open(APPROVALS_LOG, encoding="utf-8") if l.strip()]
    except FileNotFoundError:
        print("PASS verify_approvals: no log yet")
        return
    prev, legacy, chained = None, [], 0
    for i, line in enumerate(lines, 1):
        if "| chain=" not in line:
            if chained:
                print("FAIL verify_approvals: unchained line {} after chained entries".format(i))
                sys.exit(2)
            legacy.append(line)
            continue
        core, chain = line.rsplit(" | chain=", 1)
        if prev is None:
            prev = hashlib.sha256("\n".join(legacy).encode("utf-8")).hexdigest() if legacy else "genesis"
        expect = hashlib.sha256((prev + "\n" + core).encode("utf-8")).hexdigest()
        if expect != chain.strip():
            print("FAIL verify_approvals: chain broken at line {}".format(i))
            sys.exit(2)
        prev, chained = expect, chained + 1
    print("PASS verify_approvals: {} chained, {} legacy (pre-v3) entries".format(chained, len(legacy)))


if __name__ == "__main__":
    main()
