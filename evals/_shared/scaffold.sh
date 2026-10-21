#!/usr/bin/env bash
# Builds an isolated outreach project in the eval workspace (the current dir):
# the plugin's real scripts/references/templates + a fixture state overlay.
#   usage: scaffold.sh [overlay ...]      overlays: review, sent
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${EVAL_OUTREACH_REPO:-$(cd "$HERE/../.." && pwd)}"
cp -R "$REPO/scripts" "$REPO/references" "$REPO/templates" .
cp "$REPO/CLAUDE.md" . 2>/dev/null || true
cp -R "$HERE/fixture/base/." .
for o in "$@"; do cp -R "$HERE/fixture/$o/." .; done
mkdir -p data/.operator
