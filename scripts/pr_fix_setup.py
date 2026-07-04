#!/usr/bin/env python3
"""Install and status helpers for PR comment fix loop cron."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from loop_registry import app_namespace
from pr_fix_config import (
    _load_raw,
    deep_merge_missing,
    dump_overlay_yaml,
    load_config,
    operator_overlay_path,
    toolkit_example_path,
    toolkit_root,
)


LOCAL_STATE_DIRS = [
    Path(f"~/.local/share/{app_namespace()}/worktrees"),
    Path(f"~/.local/share/{app_namespace()}/pr-fix-reports"),
    Path(f"~/.local/share/{app_namespace()}/firings"),
]

LAUNCHD_LABEL = f"com.{app_namespace()}.pr-comment-fix-loop"
LAUNCHD_PLIST = Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
LATEST_MD = Path.home() / f".local/share/{app_namespace()}/pr-comment-fix-loop-latest.md"
CRON_LOG = Path.home() / f".local/share/{app_namespace()}/pr-comment-fix-loop-cron.log"


def _expand(path: Path) -> Path:
    return path.expanduser()


def gh_user() -> str:
    proc = subprocess.run(
        ["gh", "api", "user", "-q", ".login"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "gh api user failed — run gh auth login")
    return proc.stdout.strip()


def detect_primary_clone(toolkit: Path) -> str:
    env = os.environ.get("PRIMARY_CLONE", "").strip()
    if env:
        return str(Path(env).expanduser())
    parent = toolkit.parent
    if (parent / ".git").is_dir():
        return str(parent)
    return str(Path.home() / "projects/product-workspace")


def ensure_dirs() -> None:
    _expand(Path(f"~/.config/{app_namespace()}")).mkdir(parents=True, exist_ok=True)
    for d in LOCAL_STATE_DIRS:
        _expand(d).mkdir(parents=True, exist_ok=True)


def build_overlay(
    *,
    github_user: str,
    primary_clone: str,
    agent_backend: str = "claude",
    agent_model: str = "",
) -> dict[str, Any]:
    return {
        "github_user": github_user,
        "git": {"primary_clone": primary_clone},
        "agent_backend": agent_backend,
        "agent_model": agent_model,
    }


def write_overlay(cfg: dict[str, Any], path: Path | None = None) -> Path:
    target = path or operator_overlay_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump_overlay_yaml(cfg), encoding="utf-8")
    return target


def refresh_overlay(refresh: bool = False) -> Path:
    example = toolkit_example_path()
    overlay_path = operator_overlay_path()
    if not example.is_file():
        raise FileNotFoundError(f"missing toolkit example: {example}")

    if overlay_path.is_file():
        if refresh:
            base = _load_raw(example)
            existing = _load_raw(overlay_path)
            merged = deep_merge_missing(base, existing)
            overlay_path.write_text(dump_overlay_yaml(merged), encoding="utf-8")
        return overlay_path

    overlay = build_overlay(
        github_user=gh_user(),
        primary_clone=detect_primary_clone(toolkit_root()),
        agent_backend="claude",
    )
    return write_overlay(overlay)


def verify_agent_auth(backend: str, cmd: str) -> None:
    # Claude Code is the only backend. Accept, in order: (1) an explicit env
    # token/key (for CI or headless boxes with no interactive login), (2) Claude
    # Code's own stored login — the CLI runs headless under launchd using
    # ~/.claude credentials as long as HOME is preserved (the plist sets HOME).
    # Only fail if none of these are present.
    if (
        os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
        or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    ):
        return
    # Stored login check — prefer `claude auth status`, fall back to the
    # oauthAccount marker in ~/.claude.json.
    try:
        proc = subprocess.run(
            [cmd, "auth", "status"], capture_output=True, text=True, timeout=30
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0 and (
            "logged in" in out.lower() or "authenticated" in out.lower()
        ):
            return
    except (OSError, subprocess.SubprocessError):
        pass
    claude_json = Path.home() / ".claude.json"
    if claude_json.is_file():
        try:
            import json as _json

            if _json.loads(claude_json.read_text()).get("oauthAccount"):
                return
        except (OSError, ValueError):
            pass
    raise RuntimeError(
        "Claude Code auth not found — run `claude auth login` (uses your stored "
        "Claude Code session), or `claude setup-token` + export "
        "CLAUDE_CODE_OAUTH_TOKEN (or set ANTHROPIC_API_KEY) for a headless box."
    )


def verify_prereqs(cfg: dict[str, Any]) -> None:
    proc = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("gh not authenticated — run: gh auth login")

    backend = str(cfg.get("agent_backend", "claude")).lower()
    from loop_agent_config import DEFAULT_CMD

    configured = str(cfg.get("agent_cmd") or DEFAULT_CMD.get(backend, "claude"))
    cmd = configured if shutil.which(configured) else DEFAULT_CMD.get(backend, configured)
    if shutil.which(cmd) is None:
        raise RuntimeError(f"agent binary not found: {configured} (backend={backend})")

    verify_agent_auth(backend, cmd)


def render_launchd_plist(toolkit: Path, cfg: dict[str, Any]) -> str:
    home = str(Path.home())
    cron_script = toolkit / "scripts/pr-comment-fix-loop-cron.sh"
    overlay = operator_overlay_path()
    user = os.environ.get("USER", Path.home().name)

    env_lines = [
        "    <key>HOME</key>",
        f"    <string>{home}</string>",
        "    <key>USER</key>",
        f"    <string>{user}</string>",
        "    <key>PATH</key>",
        f"    <string>{home}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>",
        "    <key>PR_FIX_CONFIG</key>",
        f"    <string>{overlay}</string>",
        "    <key>PR_FIX_TOOLKIT</key>",
        f"    <string>{toolkit}</string>",
    ]
    # Namespace override — only when set, so the cron'd loop resolves the same
    # config/state/label namespace as install time (default 'kadence' needs nothing).
    ns_override = os.environ.get("KADENCE_NAMESPACE", "").strip()
    if ns_override:
        env_lines.extend(
            [
                "    <key>KADENCE_NAMESPACE</key>",
                f"    <string>{ns_override}</string>",
            ]
        )
    # Claude Code auth under launchd: prefer the long-lived OAuth token
    # (claude setup-token), fall back to an API key.
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if token:
        env_lines.extend(
            [
                "    <key>CLAUDE_CODE_OAUTH_TOKEN</key>",
                f"    <string>{token}</string>",
            ]
        )
    elif api_key:
        env_lines.extend(
            [
                "    <key>ANTHROPIC_API_KEY</key>",
                f"    <string>{api_key}</string>",
            ]
        )

    env_block = "\n".join(env_lines)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LAUNCHD_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>{cron_script}</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
{env_block}
  </dict>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Minute</key><integer>0</integer></dict>
    <dict><key>Minute</key><integer>15</integer></dict>
    <dict><key>Minute</key><integer>30</integer></dict>
    <dict><key>Minute</key><integer>45</integer></dict>
  </array>
  <key>StandardOutPath</key>
  <string>{CRON_LOG}</string>
  <key>StandardErrorPath</key>
  <string>{CRON_LOG}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
"""


def install_launchd(plist_text: str) -> None:
    LAUNCHD_PLIST.parent.mkdir(parents=True, exist_ok=True)
    LAUNCHD_PLIST.write_text(plist_text, encoding="utf-8")
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(LAUNCHD_PLIST)],
        capture_output=True,
        text=True,
    )
    load = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(LAUNCHD_PLIST)],
        capture_output=True,
        text=True,
    )
    if load.returncode != 0:
        load = subprocess.run(
            ["launchctl", "load", str(LAUNCHD_PLIST)],
            capture_output=True,
            text=True,
        )
    if load.returncode != 0:
        raise RuntimeError(load.stderr.strip() or "launchctl load failed")


def uninstall_launchd() -> None:
    if not LAUNCHD_PLIST.is_file():
        return
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(LAUNCHD_PLIST)],
        capture_output=True,
        text=True,
    )
    LAUNCHD_PLIST.unlink(missing_ok=True)


def launchd_loaded() -> bool:
    proc = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{LAUNCHD_LABEL}"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def cmd_install(args: argparse.Namespace) -> int:
    ensure_dirs()
    overlay = refresh_overlay(refresh=args.refresh_config)
    cfg = load_config(overlay)
    verify_prereqs(cfg)

    toolkit = toolkit_root()
    if not args.skip_launchd:
        install_launchd(render_launchd_plist(toolkit, cfg))

    print(f"config overlay: {overlay}")
    print(f"merged from: {toolkit_example_path()}")
    print(f"primary clone: {cfg.get('git', {}).get('primary_clone')}")
    print(f"agent_backend: {cfg.get('agent_backend')}")
    if not args.skip_launchd:
        print(f"launchd: {LAUNCHD_PLIST} (runs every 15 min — :00/:15/:30/:45)")
        print(f"cron log: {CRON_LOG}")

    if args.skip_smoke:
        return 0

    cron = toolkit / "scripts/pr-comment-fix-loop-cron.sh"
    env = {**os.environ, "PR_FIX_CONFIG": str(overlay), "PR_FIX_TOOLKIT": str(toolkit)}
    proc = subprocess.run([str(cron)], env=env, check=False)
    if LATEST_MD.is_file():
        print(f"\n--- last status ({LATEST_MD}) ---")
        print(LATEST_MD.read_text(encoding="utf-8"))
    return proc.returncode


def cmd_run(_args: argparse.Namespace) -> int:
    toolkit = toolkit_root()
    cron = toolkit / "scripts/pr-comment-fix-loop-cron.sh"
    overlay = operator_overlay_path()
    env = os.environ.copy()
    if overlay.is_file():
        env["PR_FIX_CONFIG"] = str(overlay)
    env["PR_FIX_TOOLKIT"] = str(toolkit)
    return subprocess.run([str(cron)], env=env, check=False).returncode


def cmd_status(_args: argparse.Namespace) -> int:
    overlay = operator_overlay_path()
    example = toolkit_example_path()
    print(f"toolkit example: {example}")
    print(f"operator overlay: {overlay} ({'exists' if overlay.is_file() else 'missing'})")
    print(f"launchd loaded: {launchd_loaded()}")
    print(f"local state: ~/.local/share/{app_namespace()}/")
    print("repo evidence: .sdlc/pr-fix-reports/ (on PR branch)")
    if LATEST_MD.is_file():
        print(f"\n--- {LATEST_MD} ---\n")
        print(LATEST_MD.read_text(encoding="utf-8"))
    else:
        print("\n(no firings yet — run: pr-comment-fix-loop-setup.sh run)")
    return 0


def cmd_uninstall(_args: argparse.Namespace) -> int:
    uninstall_launchd()
    print(f"removed launchd job: {LAUNCHD_LABEL}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PR comment fix loop setup")
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="dirs, config overlay, launchd, smoke test")
    p_install.add_argument("--refresh-config", action="store_true")
    p_install.add_argument("--skip-launchd", action="store_true")
    p_install.add_argument("--skip-smoke", action="store_true")
    p_install.set_defaults(func=cmd_install)

    p_run = sub.add_parser("run", help="run one cron firing now")
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser("status", help="show paths and last firing")
    p_status.set_defaults(func=cmd_status)

    p_uninstall = sub.add_parser("uninstall", help="unload launchd job")
    p_uninstall.set_defaults(func=cmd_uninstall)

    args = parser.parse_args()
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
