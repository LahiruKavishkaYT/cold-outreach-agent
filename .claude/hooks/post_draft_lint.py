#!/usr/bin/env python3
"""PostToolUse(Write|Edit): instant feedback when a draft JSON is written.

Runs the placeholder scan, the vertical-aware demo-number gate and the copy
gates on state/draft/*.json right after the writer saves it, and hands the
findings back as context, so the writer fixes problems before the critic
runs. Non-blocking: the critic's precheck is still the gate of record.
"""
import json
import os
import subprocess
import sys
from hooklib import read_input, use_project_scripts, rel, project_dir, add_context


def main():
    inp = read_input()
    ti = inp.get("tool_input") or {}
    root = project_dir(inp)
    r = rel(ti.get("file_path", ""), root)
    if not (r.startswith("state/draft/") and r.endswith(".json")):
        return
    sdir = use_project_scripts(inp)
    if not sdir:
        return
    full = os.path.join(root, r)
    try:
        json.load(open(full, encoding="utf-8"))
    except Exception as e:
        add_context("Draft {} is not valid JSON ({}). Rewrite it.".format(r, e), "PostToolUse")
    out = []
    for s in ("placeholder_scan.py", "demo_number_check.py", "content_check.py"):
        p = subprocess.run([sys.executable, os.path.join(sdir, s), full], capture_output=True,
                           text=True, timeout=30)
        out += [l for l in (p.stdout + p.stderr).splitlines() if l.startswith(("FAIL", "WARN"))]
    if out:
        add_context("Draft lint for {} (hard FAILs block approval; WARNs are craft notes):\n{}".format(
            r, "\n".join(out[:20])), "PostToolUse")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("post_draft_lint error: {}".format(e), file=sys.stderr)
        sys.exit(0)
