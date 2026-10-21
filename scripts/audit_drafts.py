#!/usr/bin/env python3
"""Run the v3 copy gates over every draft in state/draft/ and summarize.

Usage: python3 scripts/audit_drafts.py [--only-unsent] [--md outputs/draft-audit.md]

Read-only. Useful after editing guardrails.md / positioning files, or after a
model upgrade, to see how many existing drafts the gates would now block.
Dedup/suppression are skipped for already-sent drafts (they would trivially
fail dedup against their own send).
"""
import glob
import os
import re
import subprocess
import sys
from collections import Counter
from _common import STATE, ROOT, load_json, resolve_vertical

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *args):
    p = subprocess.run([sys.executable, os.path.join(HERE, script), *args], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    only_unsent = "--only-unsent" in sys.argv
    md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
    rows, fails, warns = [], Counter(), Counter()
    for path in sorted(glob.glob(os.path.join(STATE, "draft", "*.json"))):
        d = load_json(path) or {}
        sent = d.get("approval_status") == "sent_by_user" or bool(d.get("sent_date"))
        if only_unsent and sent:
            continue
        hard, warn = [], []
        for script in ("placeholder_scan.py", "demo_number_check.py", "content_check.py"):
            code, out = run(script, path)
            for line in out.splitlines():
                if line.startswith("FAIL"):
                    hard.append(line.split(":", 1)[1].strip())
                elif line.startswith("WARN"):
                    warn.append(line.split(":", 1)[1].strip())
        for h in hard:
            fails[h.split(":")[0].split("(")[0].strip()[:60]] += 1
        for w in warn:
            warns[re.sub(r"\d+", "N", w.split(";")[0].split(":")[0]).strip()[:60]] += 1
        rows.append((d.get("lead_id"), resolve_vertical(d) or "?", "sent" if sent else "unsent",
                     "BLOCK" if hard else "clear", len(warn), "; ".join(hard)[:140]))
    lines = ["| lead | vertical | status | gates | warnings | hard failures |", "|---|---|---|---|---|---|"]
    lines += ["| {} | {} | {} | {} | {} | {} |".format(*r) for r in rows]
    lines += ["", "**Hard failures by type:** " + ", ".join("{} ({})".format(k, v) for k, v in fails.most_common()),
              "", "**Warnings by type:** " + ", ".join("{} ({})".format(k, v) for k, v in warns.most_common(12))]
    blocked = sum(1 for r in rows if r[3] == "BLOCK")
    summary = "{} drafts audited, {} would be blocked by v3 hard gates".format(len(rows), blocked)
    out = "# Draft audit\n\n" + summary + "\n\n" + "\n".join(lines) + "\n"
    if md:
        path = md if os.path.isabs(md) else os.path.join(ROOT, md)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(out)
        print("wrote " + os.path.relpath(path, ROOT))
    print(summary)
    print("hard:", dict(fails.most_common()))
    print("warn:", dict(warns.most_common(12)))


if __name__ == "__main__":
    main()
