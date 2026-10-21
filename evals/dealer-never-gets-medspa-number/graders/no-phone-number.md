---
type: regex
target: { source: file, path: state/draft/lone-star-motors.json }
pattern: '\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}'
match: not_contains
weight: 3
---
