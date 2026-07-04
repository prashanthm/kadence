#!/usr/bin/env bash
# Cron wrapper: preflight → agent (review) → status report.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PR_REVIEW_LOOP_TOOLKIT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=loop_resolve_python.sh
source "$SCRIPT_DIR/loop_resolve_python.sh"
resolve_python

# Single-instance lock: skip this firing if a prior one is still running.
# macOS has no flock; use an atomic mkdir lock. The lock records the owning PID
# so a crashed firing (trap EXIT never ran) is reaped immediately rather than
# blocking for the full stale window. Falls back to an mtime threshold when the
# PID is unknown/unreadable.
LOCK_DIR="${PR_REVIEW_LOOP_LOCK_DIR:-${HOME}/.local/share/ai-sdlc/pr-review-loop.lock}"
LOCK_STALE_MIN="${PR_REVIEW_LOOP_LOCK_STALE_MIN:-120}"
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
  echo "skip: previous pr-review-loop firing still in progress ($LOCK_DIR)" >&2
  exit 0
fi
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT

if [[ -z "${PR_REVIEW_LOOP_CONFIG:-}" ]]; then
  PR_REVIEW_LOOP_CONFIG="$(SCRIPT_DIR_PY="$SCRIPT_DIR" "${PYTHON_CMD[@]}" -c "
import os, sys
sys.path.insert(0, os.environ['SCRIPT_DIR_PY'])
from pr_review_loop_config import resolve_config_path
print(resolve_config_path())
")"
  export PR_REVIEW_LOOP_CONFIG
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "error: gh not authenticated" >&2
  exit 1
fi

exec "${PYTHON_CMD[@]}" "$SCRIPT_DIR/pr_review_loop_cron.py" --config "$PR_REVIEW_LOOP_CONFIG" --json
