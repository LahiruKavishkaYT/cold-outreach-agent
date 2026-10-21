"""Shared plumbing for the outreach hooks. Stdlib only.

Each hook reads one JSON object on stdin and answers with an exit code and/or
a JSON object on stdout (see https://code.claude.com/docs/en/hooks).

PreToolUse guards FAIL CLOSED: if the guard itself crashes, the tool call is
denied (exit 2) rather than silently allowed.
"""
import json
import os
import sys

HOOK_DIR = os.path.dirname(os.path.abspath(__file__))


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def project_dir(inp=None):
    return (os.environ.get("CLAUDE_PROJECT_DIR")
            or (inp or {}).get("cwd")
            or os.path.dirname(os.path.dirname(HOOK_DIR)))


def use_project_scripts(inp=None):
    """Import scripts/_common.py from the project, pointed at the project root."""
    root = project_dir(inp)
    os.environ["OUTREACH_ROOT"] = root
    for cand in (os.path.join(root, "scripts"),
                 os.path.join(os.path.dirname(os.path.dirname(HOOK_DIR)), "scripts")):
        if os.path.isfile(os.path.join(cand, "_common.py")):
            if cand not in sys.path:
                sys.path.insert(0, cand)
            return cand
    return None


def rel(path, root):
    """Project-relative, forward-slash path ('' if outside the project)."""
    if not path:
        return ""
    p = os.path.normpath(path if os.path.isabs(path) else os.path.join(root, path))
    r = os.path.normpath(root)
    if os.path.normcase(p) == os.path.normcase(r):
        return "."
    if not os.path.normcase(p).startswith(os.path.normcase(r) + os.sep):
        return ""
    return os.path.relpath(p, r).replace(os.sep, "/")


def maintenance_mode():
    """Launch Claude with OUTREACH_MAINTENANCE=1 to let it edit .claude/ and scripts/.
    A Bash `export` inside the session cannot flip this: hooks read the env of
    the Claude Code process, which the model's shell commands don't change."""
    return os.environ.get("OUTREACH_MAINTENANCE") == "1"


def deny(reason, event="PreToolUse"):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": event,
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)


def add_context(text, event):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event,
                                             "additionalContext": text[:9500]}}))
    sys.exit(0)


def guard(main):
    """Run a PreToolUse guard; any crash becomes a denial (fail closed)."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # pragma: no cover
        print("outreach guard crashed ({}); denying to stay safe".format(e), file=sys.stderr)
        sys.exit(2)
