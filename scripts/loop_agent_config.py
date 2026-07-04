"""Shared loop agent backend config (Cursor | Copilot | Claude)."""
from __future__ import annotations

from typing import Any

VALID_BACKENDS = frozenset({"cursor", "copilot", "claude"})

DEFAULT_CMD: dict[str, str] = {
    "cursor": "agent",
    "copilot": "copilot",
    "claude": "claude",
}

TOOL_NAMES: dict[str, str] = {
    "cursor": "Cursor",
    "copilot": "GitHub Copilot",
    "claude": "Claude Code",
}

# Runtime fallback order: try cursor first, fall through to copilot, then claude
# when a firing fails (rate limit, auth, transient API error, etc.).
BACKEND_FALLBACK_CHAIN: tuple[str, ...] = ("cursor", "copilot", "claude")


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
    backend = str(cfg.get("agent_backend", "cursor")).lower().strip()
    if backend not in VALID_BACKENDS:
        backend = "cursor"
    cfg["agent_backend"] = backend
    cfg.setdefault("agent_model", str(cfg.get("agent_model") or ""))
    if not cfg.get("agent_cmd"):
        cfg["agent_cmd"] = DEFAULT_CMD[backend]
    return cfg


def agent_tool_name(cfg: dict[str, Any]) -> str:
    backend = str(cfg.get("agent_backend", "cursor")).lower()
    return TOOL_NAMES.get(backend, backend)


def resolve_agent_cmd(cfg: dict[str, Any]) -> str:
    cfg = normalize_agent_config(dict(cfg))
    return str(cfg["agent_cmd"])
