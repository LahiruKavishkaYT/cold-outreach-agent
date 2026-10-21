#!/usr/bin/env python3
"""Copy gates for a draft: hard blocks + advisory style lint.

HARD (exit 2):
  - recipient missing or malformed
  - banned phrase present (list parsed from references/guardrails.md)
  - any link in a first-touch email (deliverability rule in CLAUDE.md)
  - compliance footer missing when sender-profile.md sets require_footer: true

ADVISORY (printed as WARN, never blocks):
  - word count outside the touch's range
  - subject longer than 6 words, Title Case, or "re:/fwd:" tricks
  - more than one question mark (usually more than one ask)
  - exclamation marks, em dashes, emoji
  - AI tells: contrast reveal ("it's not X, it's Y"), self-answered question
    ("The result?"), stock openers. Source: cold-email-craft skill.
  - opens with "I" / "My name is"
  - compliance footer missing (when not required)

Usage: python3 scripts/content_check.py <draft.json> [--json]
"""
import json
import os
import re
import sys
from _common import load_draft, banned_phrases, norm_text, valid_email, REFERENCES

URL = re.compile(r"(https?://|www\.)[^\s)\]>\"']+|\b[a-z0-9-]+\.(com|ca|io|ai|co|net|org|com\.au)(/\S*)?\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
WORD_RANGES = {"first": (40, 125), "followup": (25, 100), "reply": (10, 180)}

AI_TELLS = [
    (re.compile(r"\b(it'?s|this is|that'?s)\s+not\s+(just\s+)?(about\s+)?[^.,;]{1,40}[,;.]\s*(it'?s|this is|that'?s)\b", re.I),
     "contrast reveal (\"it's not X, it's Y\")"),
    (re.compile(r"\bnot because\b[^.]{1,60}\.\s*because\b", re.I), "contrast reveal (\"not because X. Because Y\")"),
    (re.compile(r"\bno [a-z]+(?: [a-z]+)?, no [a-z]+(?: [a-z]+)?,? (?:and )?no\b", re.I), "negation list (\"no X, no Y, no Z\")"),
    (re.compile(r"(^|\n|\. )(the (result|catch|kicker|best part|truth))\?", re.I), "self-answered question"),
    (re.compile(r"\bhere'?s the thing\b", re.I), "stock phrase \"here's the thing\""),
    (re.compile(r"\bi'?ll be honest\b", re.I), "stock phrase \"I'll be honest\""),
    (re.compile(r"\b(unlock|supercharge|elevate|seamless(ly)?|leverage|game[- ]chang)", re.I), "marketing vocabulary"),
    (re.compile(r"\bi came across\b", re.I), "\"I came across\" opener"),
]


def touch_of(draft):
    t = (draft.get("touch") or "").strip().lower()
    if t in WORD_RANGES:
        return t
    if draft.get("in_reply_to") or draft.get("thread"):
        return "reply"
    return "first"


def sender_profile():
    path = os.path.join(REFERENCES, "sender-profile.md")
    prof = {"postal_address": "", "optout_line": "", "require_footer": False}
    try:
        txt = open(path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        return prof
    m = re.search(r"SENDER-PROFILE(.*?)-->", txt, re.S)
    if not m:
        return prof
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.split(" #", 1)[0].strip()
        if k == "require_footer":
            prof[k] = v.lower() in ("true", "yes", "1")
        elif k in prof and "[[MISSING" not in v:
            prof[k] = v
    return prof


def check(draft):
    hard, warn = [], []
    subject = draft.get("subject", "") or ""
    body = draft.get("body", "") or ""
    text = subject + "\n" + body
    ntext = norm_text(text)
    touch = touch_of(draft)

    # ---- HARD
    if not valid_email(draft.get("recipient", "")):
        hard.append("recipient missing or malformed: {!r}".format(draft.get("recipient")))
    for cc in (draft.get("cc") or []) + (draft.get("bcc") or []):
        if not valid_email(cc):
            hard.append("malformed cc/bcc address: {!r}".format(cc))
    for p in banned_phrases():
        if re.search(r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", ntext):
            hard.append("banned phrase: \"{}\"".format(p))
    if touch == "first":
        links = [m.group(0) for m in URL.finditer(body)]
        if links:
            hard.append("link(s) in a first-touch email: {}".format(", ".join(links[:3])))
    prof = sender_profile()
    has_footer = bool(prof["postal_address"]) and norm_text(prof["postal_address"])[:20] in ntext
    has_optout = bool(prof["optout_line"]) and norm_text(prof["optout_line"])[:25] in ntext
    if prof["require_footer"] and touch != "reply" and not (has_footer and has_optout):
        hard.append("compliance footer missing (postal address + opt-out line from references/sender-profile.md)")

    # ---- ADVISORY
    words = len(re.findall(r"\b[\w'’-]+\b", body))
    lo, hi = WORD_RANGES[touch]
    if words < lo or words > hi:
        warn.append("{} words; target for a {} touch is {}-{}".format(words, touch, lo, hi))
    sw = len(subject.split())
    if sw > 6:
        warn.append("subject is {} words; 2-5 reads as internal mail".format(sw))
    if re.match(r"^\s*(re|fwd?)\s*:", subject, re.I) and touch == "first":
        warn.append("fake Re:/Fwd: subject on a first touch")
    caps = [w for w in subject.split() if w[:1].isupper()]
    if sw >= 3 and len(caps) >= sw - 1:
        warn.append("subject is Title Case; lowercase looks less like marketing")
    q = body.count("?")
    if q > 1:
        warn.append("{} question marks; usually means more than one ask".format(q))
    if "!" in text:
        warn.append("exclamation mark(s)")
    if "—" in text or " -- " in text:
        warn.append("em dash(es); a common AI tell in cold email")
    if EMOJI.search(text):
        warn.append("emoji")
    first_line = body.strip().split("\n", 1)[0].strip().lower()
    if first_line.startswith(("i ", "i'm", "my name")):
        warn.append("opens with I/my name; lead with their world")
    for rx, label in AI_TELLS:
        if rx.search(text):
            warn.append("AI tell: " + label)
    if not prof["require_footer"] and touch != "reply" and not (has_footer and has_optout):
        if prof["postal_address"]:
            warn.append("no postal address + opt-out line (CAN-SPAM); set require_footer: true to enforce")
        else:
            warn.append("SETUP: references/sender-profile.md has no postal address; CAN-SPAM wants one in every commercial email")
    return hard, warn, {"touch": touch, "words": words}


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit("usage: content_check.py <draft.json> [--json]")
    draft = load_draft(args[0])
    hard, warn, meta = check(draft)
    if "--json" in args:
        print(json.dumps({"hard": hard, "warn": warn, **meta}))
        sys.exit(2 if hard else 0)
    for h in hard:
        print("FAIL content_check: " + h)
    for w in warn:
        print("WARN content_check: " + w)
    if hard:
        sys.exit(2)
    print("PASS content_check: {} touch, {} words, no banned phrases".format(meta["touch"], meta["words"]))


if __name__ == "__main__":
    main()
