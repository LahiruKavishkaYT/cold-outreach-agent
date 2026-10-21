# Email craft

**Vertical rule:** load the offer, proof, and canonical demo number ONLY from
`references/positioning-<vertical>.md` for this lead's vertical. Mia is med spa;
Aria is dealers. Cross-citing is a critical error.

## Shape (first-touch)
- **Subject:** 2-5 words, lowercase, looks like internal mail, no clickbait,
  no fake "Re:". Reference their world, not your product. (v3: was 4-8 words;
  shortened per the cold-email-craft subject-line data. 31 of 73 v2 drafts ran
  7+ words.)
- **Open (1 line):** the sourced personalization hook. Prove you looked.
- **Bridge (1-2 lines):** the problem that hook implies, then the offer from
  positioning.md in one plain sentence.
- **CTA (1 line):** ONE ask — a low-friction reply question ("Worth a reply?",
  "Want me to send it over?"). If the vertical's canonical demo number is set,
  include it inline mid-body as proof ("call it like a customer would:
  +1 ...") — the number is evidence, the reply is the ask. Replies also feed
  the new domain's sender reputation; calls don't. No links in first touch.
- **Total:** ~50-110 words. Shorter beats longer. One CTA only.
- **Footer:** once `references/sender-profile.md` is filled in, end with the
  postal address and opt-out line from it (CAN-SPAM).

## Voice
- Plain, direct, peer-to-peer. No corporate filler. No banned phrases.
- No exclamation stacking, no emoji, no fake urgency.
- **No em dashes.** They are the most common AI tell in cold email (45 of 73
  v2 drafts had them). Use a comma, a period, or parentheses.
- Avoid the AI-tell shapes listed in the cold-email-craft skill
  (`upstream/copywriting/references/ai-tells.md`): "it's not X, it's Y",
  "no X, no Y, no Z", self-answered questions ("The result?").

## Draft fields that drive the gates
- `vertical`: `medspa` | `dealers` (required; decides which demo number is legal)
- `touch`: `first` | `followup` | `reply` (first touch = no links, 40-125 words)
- `message_version`: short angle label (e.g. `after-hours-v2`) so status can
  compare reply rates per angle
- Don't claim results you don't have. The demo IS the proof — invite them to it.

## Follow-ups (ladder)
- **F1 (+3-4 days):** offer the 2-minute Loom — new value, not a nudge.
- **F2 (+5-7 days):** a different angle from the vertical positioning file
  (dealers: out-of-state/financing; med spa: after-hours consult questions).
- **F3 (+7 days):** short, honest close-the-loop ("If timing's wrong, one line
  and I'll stop."). Then stop — three follow-ups max, then the lead rests 90 days.
- Never "just following up". Reference the prior email lightly, don't guilt-trip.

## Replies
- Match their energy and answer the actual question first.
- Pricing question → give a real range or a clear next step, never dodge.
