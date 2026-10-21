---
type: regex
target: { source: file, path: state/draft/aurora-medspa.json }
pattern: '\\u2014|—'
match: not_contains
weight: 0.5
---
