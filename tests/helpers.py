"""Test sandbox: a throwaway project root with the real scripts, hooks and
references, but empty data/ and state/. Every test gets a fresh one."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

MEDSPA_NUMBER = "+1 (555) 010-0100"


class Sandbox:
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="outreach-test-")
        for d in ("scripts", "references", "templates"):
            shutil.copytree(os.path.join(REPO, d), os.path.join(self.root, d))
        shutil.copytree(os.path.join(REPO, ".claude", "hooks"), os.path.join(self.root, ".claude", "hooks"))
        for d in ("data/drafts/approved", "data/.operator", "state/draft", "state/research",
                  "state/batches", "outputs", "inputs"):
            os.makedirs(os.path.join(self.root, d), exist_ok=True)
        self.write("data/suppression.txt", "# test\n")
        self.write("data/outreach-log.json", "[]")
        self.write("state/leads-index.json", "{}")
        self.env = dict(os.environ, OUTREACH_ROOT=self.root, CLAUDE_PROJECT_DIR=self.root)
        self.env.pop("OUTREACH_COMPOSE_WEBHOOK", None)
        self.env.pop("OUTREACH_MAINTENANCE", None)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def path(self, rel):
        return os.path.join(self.root, rel)

    def write(self, rel, text):
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def write_json(self, rel, obj):
        return self.write(rel, json.dumps(obj, indent=2))

    def read_json(self, rel):
        with open(self.path(rel), encoding="utf-8") as fh:
            return json.load(fh)

    def script(self, name, *args):
        p = subprocess.run([PY, self.path("scripts/" + name), *args], capture_output=True,
                           text=True, env=self.env, cwd=self.root)
        return p.returncode, p.stdout + p.stderr

    def hook(self, name, payload, env_extra=None):
        env = dict(self.env, **(env_extra or {}))
        p = subprocess.run([PY, self.path(".claude/hooks/" + name)], input=json.dumps(payload),
                           capture_output=True, text=True, env=env, cwd=self.root)
        out = None
        if p.stdout.strip():
            try:
                out = json.loads(p.stdout)
            except json.JSONDecodeError:
                out = None
        return p.returncode, out, p.stderr

    def operator_says(self, text, kind=None, minutes_ago=0):
        """Simulate the UserPromptSubmit hook having captured the operator's words."""
        code, _, err = self.hook("capture_operator_input.py",
                                 {"hook_event_name": "UserPromptSubmit", "prompt": text, "session_id": "t"})
        assert code == 0, err

    def draft(self, lead="aurora-medspa", vertical="medspa", **over):
        d = {
            "lead_id": lead, "vertical": vertical, "touch": "first",
            "campaign_id": "medspa-test", "message_version": "after-hours-v1", "email_version": 1,
            "recipient": "frontdesk@auroramedspa.com", "cc": [], "bcc": [],
            "subject": "calls during treatments",
            "body": ("Hi Dana,\n\nYour site says the team books consults by phone and closes at 6pm "
                     "on weekdays, so a caller asking about laser downtime at 7pm gets voicemail and "
                     "usually books somewhere else.\n\nI build an AI receptionist that answers those "
                     "calls, covers the common pre-consult questions and books the consult. There's a "
                     "live demo you can call like a client would: {}.\n\nWorth a reply if it sounds "
                     "useful?\n\nthe operator").format(MEDSPA_NUMBER),
            "attachments": [], "personalization_evidence": [{"fact": "closes 6pm", "source": "https://auroramedspa.com/hours"}],
            "unverified_assumptions": [],
        }
        d.update(over)
        rel = "state/draft/{}.json".format(lead)
        self.write_json(rel, d)
        return self.path(rel)

    def index(self, **leads):
        self.write_json("state/leads-index.json", leads)


def iso(dt=None):
    return (dt or datetime.now(timezone.utc)).isoformat()
