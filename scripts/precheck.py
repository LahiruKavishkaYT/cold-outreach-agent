#!/usr/bin/env python3
"""Orchestrate every pre-send gate. The single command the critic runs.

Usage: python3 scripts/precheck.py <draft.json> [--window-days 14] [--json]

Runs, in order:
  HARD   suppression_check  (recipient or its @domain on the opt-out list)
  HARD   dedup_check        (already contacted within window)
  HARD   placeholder_scan   (unfilled {{...}} / [NAME] / TODO / [[MISSING]])
  HARD   demo_number_check  (number must be THIS vertical's canonical demo)
  HARD   content_check      (recipient format, banned phrases, links in first
                             touch, required compliance footer)
  ADVIS  content_check      (length, subject, CTA count, AI tells, footer)
  ADVIS  link_check         (malformed / placeholder links)

Exit 0 = all hard gates pass (advisory warnings may still print).
Exit 2 = one or more hard gates failed. The email stays in review.

This is deterministic. It is the layer the model cannot clear by assertion.
"""
import json
import os
import subprocess
import sys
from _common import load_draft

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *args):
    proc = subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                          capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: precheck.py <draft.json> [--window-days N] [--json]")
    draft_path = sys.argv[1]
    window = "14"
    if "--window-days" in sys.argv:
        window = sys.argv[sys.argv.index("--window-days") + 1]
    as_json = "--json" in sys.argv
    draft = load_draft(draft_path)
    recipient = draft.get("recipient", "") or "-"

    hard = [
        ("suppression", "suppression_check.py", [recipient]),
        ("dedup", "dedup_check.py", [recipient, window]),
        ("placeholder", "placeholder_scan.py", [draft_path]),
        ("demo_number", "demo_number_check.py", [draft_path]),
        ("content", "content_check.py", [draft_path]),
    ]
    advisory = [("links", "link_check.py", [draft_path])]

    results, failed, lines = {}, False, []
    lines.append("=== precheck: hard gates ===")
    for name, script, args in hard:
        code, out = run(script, *args)
        results[name] = {"pass": code == 0, "out": out}
        lines.append(out)
        failed = failed or code != 0
    lines.append("=== precheck: advisory ===")
    for name, script, args in advisory:
        _, out = run(script, *args)
        results[name] = {"pass": True, "out": out}
        lines.append(out)
    lines.append("=== precheck: result ===")
    verdict = "BLOCKED" if failed else "CLEARED"
    if failed:
        lines.append("BLOCKED: one or more hard gates failed. Email stays in review.")
    else:
        lines.append("CLEARED: all hard gates passed. Judgment items remain for human review.")

    if as_json:
        print(json.dumps({"verdict": verdict, "gates": results}, indent=1))
    else:
        print("\n".join(lines))
    sys.exit(2 if failed else 0)


if __name__ == "__main__":
    main()
