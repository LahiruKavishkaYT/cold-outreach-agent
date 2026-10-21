# Batch review card — format and approval rules

One card per batch of 10. Per-message review is preserved: every full body is
shown; the card just makes reviewing 10 fast.

## Card layout
```
BATCH <batch-id> · campaign <id> · vertical <v> · 10 leads
┌─── summary ────────────────────────────────────────────────
 #  lead                gates   score  hook (the sourced personalization)
 1  lone-star-motors    CLEAR   86     "ships nationwide" page + 9-6 hours
 2  tx-auto-group       CLEAR   81     20-lender financing page, closed Sun
 3  hudson-501          BLOCKED —      placeholder gate: no owner name found
 ...
└────────────────────────────────────────────────────────────
FULL DRAFTS (all 10, numbered):
--- #1 lone-star-motors → sales@lonestarmotors.example
subject: ...
<complete body>
evidence: <the sourced facts used> | assumptions: <anything unverified>
--- #2 ...
```
Blocked drafts are shown with their exact gate failure — never hidden, never
"fixed" silently.

## Approval language (explicit only — per approval-policy.md)
Counts as approval, scoped to the drafts it names:
- "Approve the batch" (= every CLEAR draft, blocked ones excluded automatically)
- "Approve all except #3 and #7"
- "Approve 1, 2, 5"
Does NOT count: "looks good", "continue", "nice", silence, or approving a batch
that has since changed (hash mismatch reopens review for the changed draft only).

For each approved draft, record their exact sentence via record_approval.py —
the same sentence may appear on multiple drafts' records; that is correct.
`record_approval.py` refuses words that aren't explicit approval or that
The operator didn't type themselves (operator log), and refuses BLOCKED drafts, so
"approve the batch" can never sweep in a blocked one.

Use plain numbered lines in the summary (#1..#10) so "approve all except #3"
maps unambiguously to lead ids. Echo the mapping back before recording.

## Held / blocked drafts
Held drafts get individual attention via /draft-email revision loop. Blocked
drafts must clear their hard gate (or be cancelled). They never ride along
with a batch approval.
