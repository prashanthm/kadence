"""Shared loop agent backend config (Claude Code — the only backend)."""
from __future__ import annotations

from typing import Any

VALID_BACKENDS = frozenset({"claude"})

DEFAULT_CMD: dict[str, str] = {
    "claude": "claude",
}

TOOL_NAMES: dict[str, str] = {
    "claude": "Claude Code",
}

# Runtime fallback order. Claude is the only backend, so the chain is a single
# entry — a firing tries claude once (no cross-tool fallback).
BACKEND_FALLBACK_CHAIN: tuple[str, ...] = ("claude",)


def cmd_for_backend(backend: str, cfg: dict[str, Any] | None = None) -> str:
    """Resolve the CLI binary for a backend. A configured agent_cmd applies only
    to the configured agent_backend; fallback backends use their default cmd."""
    backend = backend.lower().strip()
    if cfg and str(cfg.get("agent_backend", "")).lower().strip() == backend:
        configured = cfg.get("agent_cmd")
        if configured:
            return str(configured)
    return DEFAULT_CMD.get(backend, backend)


def normalize_agent_config(cfg: dict[str, Any]) -> dict[str, Any]:
    backend = str(cfg.get("agent_backend", "claude")).lower().strip()
    if backend not in VALID_BACKENDS:
        backend = "claude"
    cfg["agent_backend"] = backend
    cfg.setdefault("agent_model", str(cfg.get("agent_model") or ""))
    if not cfg.get("agent_cmd"):
        cfg["agent_cmd"] = DEFAULT_CMD[backend]
    return cfg


def agent_tool_name(cfg: dict[str, Any]) -> str:
    backend = str(cfg.get("agent_backend", "claude")).lower()
    return TOOL_NAMES.get(backend, backend)


def resolve_agent_cmd(cfg: dict[str, Any]) -> str:
    cfg = normalize_agent_config(dict(cfg))
    return str(cfg["agent_cmd"])
