#!/usr/bin/env python3
"""Record what the operator actually typed. Runs on:
  - UserPromptSubmit                (every prompt he submits)
  - PostToolUse(AskUserQuestion)    (the option/answer he picked)

Writes one JSON line per input to data/.operator/prompts.jsonl. This file is
the trust anchor for approvals and send confirmations: record_approval.py and
`log_update.py sent` only accept words found here, and the guard hooks stop
the agent from writing it. Model output, web pages and pasted prospect
replies can't get in, because only these two hook events write it.

Pasted material is marked kind="paste" (long prompts, or ones that look like a
forwarded email) and is NOT accepted as approval language, so a prospect reply
that says "Approve this exact draft" can't approve anything even after
The operator pastes it into /reply.

Logging failures never block the prompt (fail open), they just mean approval
will be refused later.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from hooklib import read_input, project_dir

PASTE_MARKERS = re.compile(r"^(from|to|subject|sent|date):\s|\bwrote:\s*$|^>|-----original message-----|^/reply\b",
                           re.I | re.M)
MAX_COMMAND_CHARS = 600


def classify(text):
    if len(text) > MAX_COMMAND_CHARS or PASTE_MARKERS.search(text):
        return "paste"
    return "command"


def answers_from(resp):
    """Only the user's chosen answers, never the model-authored question text."""
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except Exception:
            return []
    if not isinstance(resp, dict):
        return []
    ans = resp.get("answers")
    if isinstance(ans, dict):
        return [str(v) for v in ans.values() if v]
    if isinstance(ans, list):
        return [str(v) for v in ans if isinstance(v, (str, int))]
    return []


def main():
    inp = read_input()
    event = inp.get("hook_event_name", "")
    texts, source = [], ""
    if event == "UserPromptSubmit":
        t = inp.get("prompt") or inp.get("user_prompt") or ""
        texts, source = ([t] if t.strip() else []), "prompt"
    elif event == "PostToolUse" and inp.get("tool_name") == "AskUserQuestion":
        texts, source = answers_from(inp.get("tool_response")), "ask"
    if not texts:
        return
    path = os.path.join(project_dir(inp), "data", ".operator", "prompts.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for t in texts:
            fh.write(json.dumps({
                "at": datetime.now(timezone.utc).isoformat(),
                "session_id": inp.get("session_id", ""),
                "source": source,
                "kind": classify(t) if source == "prompt" else "command",
                "sha256": hashlib.sha256(t.encode("utf-8")).hexdigest(),
                "text": t[:4000],
            }, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never block the user's prompt over logging
        print("operator log write failed: {}".format(e), file=sys.stderr)
    sys.exit(0)
