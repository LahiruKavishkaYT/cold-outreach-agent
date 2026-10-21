# Sender profile (compliance footer)

`scripts/content_check.py` reads the block below. Until `postal_address` is set
it prints a SETUP warning on every draft; set `require_footer: true` to make a
missing footer a HARD block.

Why: CAN-SPAM (US) requires a valid physical postal address and a clear way to
opt out in commercial email, including 1:1 cold email. Canada's CASL and
Australia's Spam Act have their own consent and unsubscribe rules, and several
of your med-spa leads are Canadian. This file is not legal advice; check the
rules for each country you email.

<!-- SENDER-PROFILE
postal_address: [[MISSING: your mailing address or a registered PO box / virtual mailbox]]
optout_line: Not relevant? Reply "no thanks" and I won't email again.
require_footer: false
-->

Example footer the writer should append once the address is set:

```
Your Name · your-domain.example
<postal_address>
Not relevant? Reply "no thanks" and I won't email again.
```
