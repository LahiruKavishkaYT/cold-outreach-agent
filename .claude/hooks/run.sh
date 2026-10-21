#!/usr/bin/env bash
# Portable launcher for the Python hooks: works on macOS/Linux and on Windows
# (Claude Code runs hooks through Git Bash there, where `python3` may be
# missing but `python` or `py` exists).
#   usage: bash .claude/hooks/run.sh <hook_script.py>
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "outreach hooks: no python interpreter found; refusing tool call" >&2
  exit 2
fi
exec "$PY" "$HERE/$1"
