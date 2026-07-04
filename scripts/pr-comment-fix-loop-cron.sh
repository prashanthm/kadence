#!/usr/bin/env bash
# Cron wrapper: discover → agent → status report (local + PR branch evidence).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PR_FIX_TOOLKIT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Single-instance lock: skip this firing if a prior one is still running.
# macOS has no flock; use an atomic mkdir lock. The lock records the owning PID
# so a crashed firing (trap EXIT never ran) is reaped immediately rather than
# blocking for the full stale window. Falls back to an mtime threshold when the
# PID is unknown/unreadable.
LOCK_DIR="${PR_FIX_LOCK_DIR:-${HOME}/.local/share/ai-sdlc/pr-comment-fix-loop.lock}"
LOCK_STALE_MIN="${PR_FIX_LOCK_STALE_MIN:-120}"
mkdir -p "$(dirname "$LOCK_DIR")"
if [[ -d "$LOCK_DIR" ]]; then
  lock_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [[ "$lock_pid" =~ ^[0-9]+$ ]] && ! kill -0 "$lock_pid" 2>/dev/null; then
    echo "reaping orphaned lock (owner PID $lock_pid dead): $LOCK_DIR" >&2
    rm -rf "$LOCK_DIR"
  elif find "$LOCK_DIR" -prune -mmin +"$LOCK_STALE_MIN" 2>/dev/null | grep -q .; then
    echo "reaping stale lock (> ${LOCK_STALE_MIN}m): $LOCK_DIR" >&2
    rm -rf "$LOCK_DIR"
  fi
fi
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "skip: previous pr-comment-fix-loop firing still in progress ($LOCK_DIR)" >&2
  exit 0
fi
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT

if [[ -z "${PR_FIX_CONFIG:-}" ]]; then
  PR_FIX_CONFIG="$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from pr_fix_config import resolve_config_path
print(resolve_config_path())
")"
  export PR_FIX_CONFIG
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh not authenticated" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/pr_fix_cron.py" --config "$PR_FIX_CONFIG" --json
