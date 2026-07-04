#!/usr/bin/env bash
# Setup, run, and status for the PR review loop cron.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PR_REVIEW_LOOP_TOOLKIT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH:-/usr/bin:/bin}"

# shellcheck source=loop_resolve_python.sh
source "$SCRIPT_DIR/loop_resolve_python.sh"

usage() {
  cat <<'EOF'
Usage: pr-review-loop-setup.sh <command>

Commands:
  install   Create dirs, operator overlay, platform scheduler, smoke test
  run       Run one cron firing now
  status    Show paths, scheduler state, and last firing report
  uninstall Remove the platform scheduler job

Platform schedulers:
  macOS   launchd at :00/:15/:30/:45
  Windows Task Scheduler every 15 min (task: ai-sdlc-pr-review-loop)

Install options (pass after install):
  --refresh-config   Merge new keys from toolkit config.example.yaml
  --skip-launchd     Config only; do not install scheduler (launchd / Task Scheduler)
  --skip-smoke       Do not run cron after install
EOF
}

CMD="${1:-}"
if [[ -z "$CMD" ]]; then usage >&2; exit 1; fi
shift || true

case "$CMD" in
  install|run|status|uninstall)
    resolve_python
    exec "${PYTHON_CMD[@]}" "$SCRIPT_DIR/pr_review_loop_setup.py" "$CMD" "$@" ;;
  -h|--help|help) usage ;;
  *) echo "error: unknown command: $CMD" >&2; usage >&2; exit 1 ;;
esac
