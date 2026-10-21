#!/usr/bin/env python3
"""Hard gate: block if recipient (or its whole domain) is on the suppression list.

Usage: python3 scripts/suppression_check.py <recipient_email>
Exit 0 = not suppressed. Exit 2 = suppressed (block before drafting).

data/suppression.txt accepts full addresses and '@domain.com' lines.
"""
import sys
from _common import is_suppressed, normalize_email


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: suppression_check.py <recipient_email>")
    addr = normalize_email(sys.argv[1])
    if is_suppressed(addr):
        print("FAIL suppression_check: {} is on the suppression list".format(addr))
        sys.exit(2)
    print("PASS suppression_check: {} not suppressed".format(addr))


if __name__ == "__main__":
    main()
