"""Shared helpers for the outreach-studio-agent gate scripts.

Stdlib only. No third-party packages. Python 3.9+.

These scripts are the deterministic enforcement layer. The agent calls them
via Bash; their exit codes are gates the model cannot satisfy by assertion.
Exit 0 = pass. Non-zero = fail/block.

Paths resolve from OUTREACH_ROOT if set (used by tests and evals), otherwise
from the repo root (parent of scripts/).
"""
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

ROOT = os.environ.get("OUTREACH_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

DATA = os.path.join(ROOT, "data")
STATE = os.path.join(ROOT, "state")
REFERENCES = os.path.join(ROOT, "references")
SUPPRESSION_FILE = os.path.join(DATA, "suppression.txt")
OUTREACH_LOG = os.path.join(DATA, "outreach-log.json")
APPROVALS_LOG = os.path.join(DATA, "approvals.log")
OPERATOR_DIR = os.path.join(DATA, ".operator")
OPERATOR_LOG = os.path.join(OPERATOR_DIR, "prompts.jsonl")
INDEX = os.path.join(STATE, "leads-index.json")

VERTICALS = ("medspa", "dealers")
APPROVAL_TTL_DAYS = 7

# Canonical fields that define the identity of an approved message.
# Any change to any of these invalidates a prior approval (hash mismatch).
HASH_FIELDS = ["recipient", "cc", "bcc", "subject", "body", "attachments"]

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def now_utc():
    return datetime.now(timezone.utc)


def iso_now():
    return now_utc().isoformat()


def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json_atomic(path, obj, indent=2, sort_keys=False):
    """Write JSON via temp file + rename so a crash never leaves half a file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def normalize_email(addr):
    return (addr or "").strip().lower()


def valid_email(addr):
    return bool(EMAIL_RE.match((addr or "").strip()))


def norm_text(s):
    """Lowercase, collapse whitespace, strip curly quotes — for phrase matching."""
    s = (s or "").replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def canonical_content(draft):
    """Deterministic string over the identity fields, for hashing.

    Order-stable and whitespace-trimmed so cosmetic noise doesn't change the
    hash, but any real change to recipient/subject/body/etc. does.
    """
    parts = []
    for field in HASH_FIELDS:
        val = draft.get(field, "")
        if isinstance(val, list):
            val = ",".join(normalize_email(v) if isinstance(v, str) else json.dumps(v, sort_keys=True)
                           for v in val)
        parts.append("{}={}".format(field, str(val).strip()))
    return "\n".join(parts)


def content_hash(draft):
    return hashlib.sha256(canonical_content(draft).encode("utf-8")).hexdigest()


def load_suppression():
    out = set()
    try:
        with open(SUPPRESSION_FILE, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line:
                    out.add(normalize_email(line))
    except FileNotFoundError:
        pass
    return out


def suppressed_domains():
    """Lines like '@example.com' suppress a whole domain."""
    return {s[1:] for s in load_suppression() if s.startswith("@")}


def is_suppressed(addr):
    addr = normalize_email(addr)
    if not addr:
        return False
    if addr in load_suppression():
        return True
    dom = addr.split("@")[-1]
    return dom in suppressed_domains()


def load_draft(path):
    draft = load_json(path)
    if draft is None:
        raise SystemExit("FAIL: could not read draft JSON at {}".format(path))
    return draft


def load_index():
    return load_json(INDEX, {}) or {}


# ---------------------------------------------------------------- verticals
def infer_vertical_from_campaign(campaign_id):
    cid = (campaign_id or "").lower()
    if "dealer" in cid or "auto" in cid:
        return "dealers"
    if "spa" in cid or "med" in cid:
        return "medspa"
    return ""


def resolve_vertical(draft):
    """draft.vertical -> leads-index vertical -> campaign_id inference -> ''."""
    v = (draft.get("vertical") or "").strip().lower()
    if v in VERTICALS:
        return v
    rec = load_index().get(draft.get("lead_id", ""), {})
    v = (rec.get("vertical") or "").strip().lower()
    if v in VERTICALS:
        return v
    return infer_vertical_from_campaign(draft.get("campaign_id"))


# ---------------------------------------------------------- canonical numbers
DIGITS = re.compile(r"\d")


def digits_only(s):
    return "".join(DIGITS.findall(s or ""))


def canonical_numbers_by_vertical():
    """{vertical: {digits,...}} from references/positioning-<vertical>.md."""
    out = {}
    for v in VERTICALS:
        path = os.path.join(REFERENCES, "positioning-{}.md".format(v))
        nums = set()
        try:
            txt = open(path, "r", encoding="utf-8").read()
        except FileNotFoundError:
            out[v] = nums
            continue
        for block in re.finditer(r"CANONICAL-DEMO-NUMBERS(.*?)-->", txt, re.S):
            for line in block.group(1).splitlines():
                line = line.split("#", 1)[0].strip()
                if "[[MISSING" in line:
                    continue  # unset placeholder never becomes canonical
                d = digits_only(line)
                if len(d) >= 7:
                    nums.add(d)
        out[v] = nums
    return out


# ------------------------------------------------------------ banned phrases
def banned_phrases():
    """Parse the banned list from references/guardrails.md (single source)."""
    path = os.path.join(REFERENCES, "guardrails.md")
    try:
        txt = open(path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        return []
    m = re.search(r"## Banned phrases[^\n]*\n(.*?)(\n## |\Z)", txt, re.S)
    if not m:
        return []
    block = m.group(1)
    out = []
    for raw in re.split(r"[·\n]", block):
        p = raw.strip(" -*\t")
        p = re.sub(r"\(.*?\)", "", p).strip()  # drop "(as the whole hook)" notes
        if p and not p.startswith("<!--"):
            out.append(norm_text(p))
    return [p for p in out if p]


# Placeholder patterns that must never survive into an approved draft.
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{.*?\}\}"),            # {{first_name}}
    re.compile(r"\[[A-Z][A-Z _-]{2,}\]"),  # [NAME], [COMPANY NAME]
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\blorem ipsum\b", re.IGNORECASE),
    re.compile(r"\bXXX+\b"),
    re.compile(r"\[\[MISSING:.*?\]\]"),    # research gap markers must be resolved
    re.compile(r"<\s*(first[_ ]?name|company|name)\s*>", re.IGNORECASE),
]


# ------------------------------------------------------------ operator log
# The operator log is written ONLY by the UserPromptSubmit hook (and the
# AskUserQuestion PostToolUse hook). It is the trust anchor that proves a
# sentence was typed by the human, not produced by the model or a web page.
def operator_entries(max_age_minutes=None, include_pastes=False):
    """Recent human inputs. Pasted material (kind="paste": long prompts or
    forwarded-email text) is excluded unless include_pastes=True, so text that
    the operator pasted from a prospect can never count as their approval."""
    out = []
    cutoff = None
    if max_age_minutes is not None:
        cutoff = now_utc() - timedelta(minutes=max_age_minutes)
    try:
        with open(OPERATOR_LOG, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if cutoff is not None:
                    try:
                        when = datetime.fromisoformat(e.get("at", "").replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if when < cutoff:
                        continue
                if e.get("kind") == "paste" and not include_pastes:
                    continue
                out.append(e)
    except FileNotFoundError:
        pass
    return out


def operator_said(text, max_age_minutes=180):
    """True if `text` (normalized) appears inside a recent human prompt."""
    needle = norm_text(text)
    if len(needle) < 3:
        return False
    for e in operator_entries(max_age_minutes):
        if needle in norm_text(e.get("text", "")):
            return True
    return False


# ------------------------------------------------------- explicit approval
_NEG = re.compile(r"\b(don'?t|do not|not|never|no need to|hold off|wait)\b[^.]{0,20}\b(approve|create|save|mark)", re.I)
_APPROVAL_PATTERNS = [
    r"\bapprove(d)?\b[^.\n]{0,40}\b(this|these|it|them|draft|drafts|version|batch|all|everything|#\s?\d+|\d+(\s*[,&-]\s*\d+)*)\b",
    r"\b(this|that|the) (exact )?(version|draft) is approved\b",
    r"\bsave (this|these|them|it)( version)? as (a )?(gmail )?drafts?\b",
    r"\bcreate (the |a )?gmail drafts?\b",
    r"\bmark (this|these|them|it) ready to send\b",
]


def is_explicit_approval(text):
    t = norm_text(text)
    if not t or _NEG.search(t):
        return False
    return any(re.search(p, t, re.I) for p in _APPROVAL_PATTERNS)
