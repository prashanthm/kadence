#!/usr/bin/env bash
# Resolve a Python interpreter for loop shell wrappers (python3 → python → py -3).
resolve_python() {
  if [[ -n "${LOOP_PYTHON_CMD:-}" ]]; then
    # shellcheck disable=SC2206
    PYTHON_CMD=($LOOP_PYTHON_CMD)
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=(python3)
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    PYTHON_CMD=(python)
    return 0
  fi
  if command -v py >/dev/null 2>&1; then
    PYTHON_CMD=(py -3)
    return 0
  fi
  echo "error: python not found (tried python3, python, py -3; or set LOOP_PYTHON_CMD)" >&2
  return 1
}
