#!/usr/bin/env bash
# Invoke loop agent (Claude Code CLI) with backend-specific flags.
set -euo pipefail

usage() {
  echo "Usage: invoke_loop_agent.sh <config> <prompt-file> <workspace>" >&2
  exit 1
}

[[ $# -ge 3 ]] || usage

CONFIG="$1"
PROMPT_FILE="$2"
WORKSPACE="$3"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=loop_resolve_python.sh
source "$SCRIPT_DIR/loop_resolve_python.sh"
resolve_python

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "error: missing prompt file: $PROMPT_FILE" >&2
  exit 1
fi

if [[ ! -d "$WORKSPACE" ]]; then
  echo "error: missing workspace: $WORKSPACE" >&2
  exit 1
fi

IFS=$'\t' read -r BACKEND AGENT_CMD AGENT_MODEL < <(SCRIPT_DIR_PY="$SCRIPT_DIR" CONFIG_PY="$CONFIG" "${PYTHON_CMD[@]}" -c "
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ['SCRIPT_DIR_PY'])
config_path = Path(os.environ['CONFIG_PY'])
if 'engineering-work-loop' in config_path.name:
    from engineering_work_loop_config import load_config
elif 'pr-review-loop' in config_path.name:
    from pr_review_loop_config import load_config
else:
    from pr_fix_config import load_config
from loop_agent_config import normalize_agent_config, cmd_for_backend, VALID_BACKENDS
cfg = normalize_agent_config(load_config(os.environ['CONFIG_PY']))
# AGENT_BACKEND_OVERRIDE lets the cron retry the same firing on a fallback backend.
override = os.environ.get('AGENT_BACKEND_OVERRIDE', '').lower().strip()
backend = override if override in VALID_BACKENDS else cfg.get('agent_backend', 'claude')
agent_cmd = cmd_for_backend(backend, cfg)
print('\t'.join([backend, agent_cmd, cfg.get('agent_model', '')]))
")

AGENT_CMD="${AGENT_CMD_OVERRIDE:-$AGENT_CMD}"
export PATH="${HOME}/.local/bin:${PATH:-/usr/bin:/bin}"

if ! command -v "$AGENT_CMD" >/dev/null 2>&1; then
  echo "error: agent binary not found: $AGENT_CMD (backend=$BACKEND)" >&2
  exit 1
fi

PROMPT_TEXT="$(cat "$PROMPT_FILE")"

case "$BACKEND" in
  claude)
    # Claude Code uses the current working directory as its workspace (no
    # --workspace flag); cd in, then grant the same dir via --add-dir.
    cd "$WORKSPACE"
    CLAUDE_ARGS=(-p "$PROMPT_TEXT" --permission-mode bypassPermissions --add-dir "$WORKSPACE")
    if [[ -n "$AGENT_MODEL" ]]; then
      CLAUDE_ARGS+=(--model "$AGENT_MODEL")
    fi
    exec "$AGENT_CMD" "${CLAUDE_ARGS[@]}"
    ;;
  *)
    echo "error: unknown agent_backend: $BACKEND (expected claude)" >&2
    exit 1
    ;;
esac
