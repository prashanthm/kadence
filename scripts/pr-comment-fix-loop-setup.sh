#!/usr/bin/env bash
# Setup, run, and status for PR comment fix loop cron.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PR_FIX_TOOLKIT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH:-/usr/bin:/bin}"

usage() {
  cat <<'EOF'
Usage: pr-comment-fix-loop-setup.sh <command>

Commands:
  install   Create dirs, operator config overlay, launchd (:15/:45), smoke test
  run       Run one cron firing now
  status    Show paths and last firing report
  uninstall Remove launchd job

Install options (pass after install):
  --refresh-config   Merge new keys from toolkit config.example.yaml
  --skip-launchd     Config only; do not install launchd
  --skip-smoke       Do not run cron after install

Examples:
  agent login                  # once, before install (Cursor)
  copilot login                # once, before install (Copilot)
  pr-comment-fix-loop-setup.sh install
  pr-comment-fix-loop-setup.sh run
  pr-comment-fix-loop-setup.sh status
EOF
}

CMD="${1:-}"
if [[ -z "$CMD" ]]; then
  usage >&2
  exit 1
fi
shift || true

case "$CMD" in
  install|run|status|uninstall)
    exec python3 "$SCRIPT_DIR/pr_fix_setup.py" "$CMD" "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "error: unknown command: $CMD" >&2
    usage >&2
    exit 1
    ;;
esac
