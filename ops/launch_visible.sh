#!/bin/sh
# Deterministic launch of Pyrnova's visible surfaces for owner inspection.
#   - Customer product (Customer Lens / Opportunities / Decision / Evidence / AS-OF / Brief)
#   - Public website preview (informational, intake-disabled State 1)  [optional]
#
# Usage:
#   ops/launch_visible.sh            # start customer product on :8765 (local dev, no auth)
#   ops/launch_visible.sh --website  # also build + preview the public website on :4318
#
# Run from the repository root (/Users/stu/Documents/Pyrnova-intl).
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "Pyrnova visible surfaces"
echo "  repo: $ROOT"
echo

if [ "${1:-}" = "--website" ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "Public website: building + previewing (informational, intake disabled)..."
    echo "  → http://127.0.0.1:4318/"
    ( cd website-go && npm run serve ) &
    WEB_PID=$!
    trap 'kill "$WEB_PID" 2>/dev/null || true' INT TERM EXIT
    sleep 1
  else
    echo "npm not found — skipping website preview." >&2
  fi
  echo
fi

echo "Customer product: starting on http://127.0.0.1:8765"
echo "  /               customer product  (pick tenant: torch or dap)"
echo "  /material.html  Decision View / Material Changes / AS-OF"
echo "  /console        operator console (local-only)"
echo "  (Ctrl-C to stop)"
echo
exec "$PY" -m pyrnova.ops_server --host 127.0.0.1 --port 8765
