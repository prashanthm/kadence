#!/usr/bin/env bash
# Setup, run, and status for engineering work loop cron.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ENGINEERING_LOOP_TOOLKIT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH:-/usr/bin:/bin}"

# shellcheck source=loop_resolve_python.sh
source "$SCRIPT_DIR/loop_resolve_python.sh"

usage() {
  cat <<'EOF'
Usage: engineering-work-loop-setup.sh [--loop <name>] <command>

Loops (family members over the shared engine):
  --loop implement-loop   Build: Ready for Dev → writes code → code PR (default)
  --loop spec-loop        Spec:  Ready for Spec → authors specs/<slug>/ → spec PR
  (pr-review-loop / pr-comment-fix-loop have their own setup scripts)

Commands:
  install   Create dirs, operator config overlay, platform scheduler, smoke test
  run       Run one cron firing now
  status    Show paths, scheduler state, and last firing report
  uninstall Remove the platform scheduler job

Platform schedulers:
  macOS   launchd at :00/:15/:30/:45
  Windows Task Scheduler every 15 min (task: ai-sdlc-<loop> or ai-sdlc-<inst>-<loop>)

Install options (pass after install):
  --refresh-config   Merge new keys from toolkit config.example.yaml
  --skip-launchd     Config only; do not install scheduler (launchd / Task Scheduler)
  --skip-smoke       Do not run cron after install

Examples:
  agent login                  # once, before install (Cursor)
  copilot login                # once, before install (Copilot)
  engineering-work-loop-setup.sh install
  engineering-work-loop-setup.sh run
  engineering-work-loop-setup.sh status
EOF
}

# Optional leading `--loop <name>` selects the family member (implement-loop |
# spec-loop). It is a global arg on the Python entrypoint, so it must precede the
# subcommand there.
LOOP_ARGS=()
if [[ "${1:-}" == "--loop" ]]; then
  LOOP_ARGS=(--loop "${2:?--loop needs a value}")
  shift 2
fi

CMD="${1:-}"
if [[ -z "$CMD" ]]; then
  usage >&2
  exit 1
fi
shift || true

case "$CMD" in
  install|run|status|uninstall)
    resolve_python
    exec "${PYTHON_CMD[@]}" "$SCRIPT_DIR/engineering_work_loop_setup.py" ${LOOP_ARGS[@]+"${LOOP_ARGS[@]}"} "$CMD" "$@"
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
