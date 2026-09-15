#!/usr/bin/env bash
# Pyrnova single-node deploy wrapper (B4.6). Docker-free; wraps `python -m pyrnova.release`.
#
#   deploy.sh stage   <source_checkout>   # stage an immutable release from a git checkout at HEAD
#   deploy.sh activate <sha>              # atomically activate + restart + health-check
#   deploy.sh rollback                    # roll CODE back to the previous release (state untouched)
#   deploy.sh current | history
#
# Env: PYRNOVA_RELEASE_ROOT (default /srv/pyrnova), PYRNOVA_VENV (default $ROOT/venv),
#      PYRNOVA_SERVICES (default "pyrnova-web pyrnova-live-ops"), PYRNOVA_HEALTH_URL.
set -euo pipefail

ROOT="${PYRNOVA_RELEASE_ROOT:-/srv/pyrnova}"
VENV="${PYRNOVA_VENV:-$ROOT/venv}"
PY="$VENV/bin/python"
SERVICES="${PYRNOVA_SERVICES:-pyrnova-web pyrnova-live-ops}"
HEALTH_URL="${PYRNOVA_HEALTH_URL:-http://127.0.0.1:8765/healthz}"
cmd="${1:-}"; shift || true

restart_services() {
  for svc in $SERVICES; do
    echo "restarting $svc"
    sudo systemctl restart "$svc"
  done
}

verify_health() {
  # Fail closed: a non-200 (or unreachable) endpoint makes the deploy visibly fail.
  for _ in $(seq 1 10); do
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then echo "health OK ($HEALTH_URL)"; return 0; fi
    sleep 2
  done
  echo "HEALTH CHECK FAILED ($HEALTH_URL)" >&2
  return 1
}

case "$cmd" in
  stage)    "$PY" -m pyrnova.release --root "$ROOT" stage --source "${1:?source checkout required}" ;;
  activate) "$PY" -m pyrnova.release --root "$ROOT" activate "${1:?sha required}"; restart_services; verify_health ;;
  rollback) "$PY" -m pyrnova.release --root "$ROOT" rollback; restart_services; verify_health ;;
  current)  "$PY" -m pyrnova.release --root "$ROOT" current ;;
  history)  "$PY" -m pyrnova.release --root "$ROOT" history ;;
  *) echo "usage: deploy.sh {stage <src>|activate <sha>|rollback|current|history}" >&2; exit 2 ;;
esac
