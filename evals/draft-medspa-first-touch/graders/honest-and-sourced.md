---
type: llm
focus: { source: file, path: state/draft/aurora-medspa.json }
weight: 2
---
Judge only the "subject" and "body" fields.
Verified lead facts: Aurora Med Spa in Boise; owner and only injector Dana; consults booked by phone ("Call us to book your free skin consult"); closed Sunday and Monday; weekday hours end 6pm; Vagaro online booking; services laser hair removal, HydraFacial, Botox and fillers.
Allowed offer framing (from the seller's own positioning file, not lead facts): callers often have a pre-consult question (candidacy, downtime) and may not leave a voicemail; the AI receptionist answers calls any hour, handles common pre-consult questions, and books or routes consults into the clinic's existing calendar. The only proof is a live demo at +1 (555) 010-0100, presented as a demo.
PASS if the email uses only the facts and framing above, presents the demo as a demo (not a client), has one reply-based ask, and contains no statistic, percentage, client name, testimonial, or claimed result.
FAIL if it states any number-based claim (e.g. "clinics lose 30% of calls"), implies existing med-spa clients or results, asserts a lead fact not listed (e.g. a staff count or that calls definitely go unanswered), or makes more than one ask.
