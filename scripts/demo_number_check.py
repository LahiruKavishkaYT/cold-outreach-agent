#!/usr/bin/env python3
"""Hard gate: every phone number in a draft must be the canonical demo number
for THAT LEAD'S VERTICAL.

Canonical numbers live in references/positioning-<vertical>.md:
    <!-- CANONICAL-DEMO-NUMBERS
    +1 555 010 0100   # Mia (med spa)
    -->

v3 change: v2 accepted a number from ANY positioning file, so Mia's med-spa
number on a dealer email passed the gate. Now the vertical is resolved
(draft.vertical -> leads-index -> campaign_id) and only that file's numbers
count. A cross-vertical number is reported explicitly.

Usage: python3 scripts/demo_number_check.py <draft.json>
Exit 0 = pass. Exit 2 = block.
"""
import re
import sys
from _common import (load_draft, resolve_vertical, canonical_numbers_by_vertical,
                     digits_only)

# Structured phone shapes (US/CA "+1 (555) 010-0100", AU "02 9876 5432",
# "0412 345 678", "+61 2 9876 5432"). v3: v2 matched any run of 7+ digits,
# so dealer copy like "the 2019 911" or "2018-2021 models" was read as a
# phone number and blocked.
PHONE = re.compile(r"(?<![\w])(?:\+\d{1,3}[\s.-]?|\d{1,3}[\s.-])?(?:\(\d{1,4}\)|\d{1,4})[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?![\w])")
DATEISH = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def find_numbers(text):
    out = []
    for m in PHONE.finditer(text):
        s = m.group(0).strip()
        if DATEISH.match(s):
            continue
        groups = re.findall(r"\d+", s)
        if len(groups) >= 2 and all(len(g) == 4 and g[:2] in ("19", "20") for g in groups):
            continue  # a run of model years, not a phone number
        n = len(digits_only(s))
        if 9 <= n <= 15:
            out.append(s)
    return out


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: demo_number_check.py <draft.json>")
    draft = load_draft(sys.argv[1])
    text = "{}\n{}".format(draft.get("subject", ""), draft.get("body", ""))
    found = find_numbers(text)
    if not found:
        print("PASS demo_number_check: no phone numbers in draft")
        return
    vertical = resolve_vertical(draft)
    canon = canonical_numbers_by_vertical()
    if not vertical:
        print("FAIL demo_number_check: draft has a phone number but the lead's vertical "
              "is unknown (set draft.vertical or the leads-index vertical)")
        sys.exit(2)
    mine = canon.get(vertical, set())
    others = {d: v for v, nums in canon.items() if v != vertical for d in nums}
    bad = []
    for num in found:
        d = digits_only(num)
        # tolerate a leading country code difference (+1)
        ok = d in mine or any(d.endswith(c) or c.endswith(d) for c in mine if len(d) >= 10)
        if ok:
            continue
        if d in others:
            bad.append("{} is the {} demo number — wrong vertical ({})".format(num, others[d], vertical))
        else:
            bad.append("{} is not a canonical {} demo number".format(num, vertical))
    if bad:
        if not mine:
            bad.append("references/positioning-{}.md has no canonical number set".format(vertical))
        print("FAIL demo_number_check: " + "; ".join(bad))
        sys.exit(2)
    print("PASS demo_number_check: number(s) match the canonical {} demo".format(vertical))


if __name__ == "__main__":
    main()
