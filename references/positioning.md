# Positioning — vertical router

This system runs **two campaigns with separate offers**. Every lead carries a
`vertical`; the writer and critic MUST load the matching file and may only use
proof/CTA/demo numbers from it:

| vertical | file | demo proof |
|---|---|---|
| `medspa`  | `references/positioning-medspa.md`  | Mia — med-spa AI receptionist (callable) |
| `dealers` | `references/positioning-dealers.md` | Aria — auto-dealer AI agent (callable) |

Never cite the med-spa demo to a dealer or vice versa. A lead with no vertical
is a routing error — resolve it before drafting (infer from the CSV/campaign,
confirm with the operator if ambiguous).

Canonical demo numbers live in each vertical file's CANONICAL-DEMO-NUMBERS
block; `scripts/demo_number_check.py` reads all `positioning*.md` files.

`scripts/demo_number_check.py` resolves each draft's vertical
(draft.vertical -> leads-index -> campaign_id) and accepts ONLY that vertical's
numbers. A med-spa number in a dealer email is a hard block.
