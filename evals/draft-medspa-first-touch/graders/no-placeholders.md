---
type: regex
target: { source: file, path: state/draft/aurora-medspa.json }
pattern: '"(subject|body)"\s*:\s*"(?:[^"\\]|\\.)*?(\[\[MISSING|\{\{|\[NAME\]|\bTODO\b)'
match: not_contains
weight: 2
---
