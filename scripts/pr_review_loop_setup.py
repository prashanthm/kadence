#!/usr/bin/env python3
"""Install / status helpers for the PR review loop cron (reuses pr_fix_setup
shared helpers; review-loop-specific labels, env, and plist)."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from pr_review_loop_config import (
    build_overlay_yaml,
    deep_merge_missing,
    load_config,
    operator_overlay_path,
    toolkit_example_path,
    toolkit_root,
)
from loop_registry import app_namespace
from pr_fix_config import _load_raw
from pr_fix_setup import (
    detect_primary_clone,
    gh_user,
    verify_agent_auth,
)

LAUNCHD_LABEL = f"com.{app_namespace()}.pr-review-loop"
LAUNCHD_PLIST = Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL}.plist"
WINDOWS_TASK_NAME = f"{app_namespace()}-pr-review-loop"
CRON_SCRIPT_RELATIVE = Path("scripts/pr-review-loop-cron.sh")
WINDOWS_TASK_SCRIPT = Path.home() / f".local/share/{app_namespace()}/pr-review-loop-task.ps1"
LATEST_MD = Path.home() / f".local/share/{app_namespace()}/pr-review-loop-latest.md"
CRON_LOG = Path.home() / f".local/share/{app_namespace()}/pr-review-loop-cron.log"


def is_windows() -> bool:
    return os.name == "nt"


def scheduler_name() -> str:
    return "Task Scheduler" if is_windows() else "launchd"


def scheduler_details() -> str:
    if is_windows():
        return f"{WINDOWS_TASK_NAME} (runs every 15 min)"
    return f"{LAUNCHD_PLIST} (runs every 15 min — :00/:15/:30/:45)"


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _is_usable_bash(path: str) -> bool:
    p = Path(path)
    parts = {part.lower() for part in p.parts}
    return p.is_file() and not ({"windows", "system32"} <= parts)


def resolve_bash() -> str:
    override = os.environ.get("BASH_EXE", "").strip()
    candidates: list[str] = []
    if override:
        candidates.append(override)
    located = shutil.which("bash")
    if located:
        candidates.append(located)

    for root in (
        os.environ.get("ProgramW6432", ""),
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("LocalAppData", ""),
    ):
        if not root:
            continue
        base = Path(root)
        candidates.extend(
            [
                str(base / "Git/bin/bash.exe"),
                str(base / "Git/usr/bin/bash.exe"),
                str(base / "Programs/Git/bin/bash.exe"),
                str(base / "Programs/Git/usr/bin/bash.exe"),
            ]
        )

    seen: set[str] = set()
    for candidate in candidates:
        normalized = str(Path(candidate))
        if normalized in seen:
            continue
        seen.add(normalized)
        if _is_usable_bash(normalized):
            return normalized

    raise RuntimeError(
        "usable bash not found — install Git Bash or set BASH_EXE to bash.exe"
    )


def render_windows_task_script(toolkit: Path, cfg: dict[str, Any]) -> str:
    overlay = operator_overlay_path()
    cron_script = toolkit / CRON_SCRIPT_RELATIVE
    home = str(Path.home())
    bash = resolve_bash()
    lines = [
        "$env:HOME=" + _ps_quote(home),
        "$env:USERPROFILE=" + _ps_quote(home),
        "$env:PR_REVIEW_LOOP_CONFIG=" + _ps_quote(str(overlay)),
        "$env:PR_REVIEW_LOOP_TOOLKIT=" + _ps_quote(str(toolkit)),
    ]

    ns_override = os.environ.get("KADENCE_NAMESPACE", "").strip()
    if ns_override:
        lines.append("$env:KADENCE_NAMESPACE=" + _ps_quote(ns_override))
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if token:
        lines.append("$env:CLAUDE_CODE_OAUTH_TOKEN=" + _ps_quote(token))
    elif api_key:
        lines.append("$env:ANTHROPIC_API_KEY=" + _ps_quote(api_key))

    lines.append("& " + _ps_quote(bash) + " " + _ps_quote(str(cron_script)))
    return "\n".join(lines) + "\n"


def write_windows_task_script(toolkit: Path, cfg: dict[str, Any]) -> Path:
    WINDOWS_TASK_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    WINDOWS_TASK_SCRIPT.write_text(render_windows_task_script(toolkit, cfg), encoding="utf-8")
    return WINDOWS_TASK_SCRIPT


def render_windows_task_command(script_path: Path) -> str:
    return (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        f'"{script_path}"'
    )


def ensure_dirs() -> None:
    (Path.home() / f".config/{app_namespace()}").mkdir(parents=True, exist_ok=True)
    (Path.home() / f".local/share/{app_namespace()}").mkdir(parents=True, exist_ok=True)


def build_overlay(*, github_user: str, primary_clone: str,
                  agent_backend: str = "claude", agent_model: str = "") -> dict[str, Any]:
    return {
        "github_user": github_user,
        "git": {"primary_clone": primary_clone},
        "agent_backend": agent_backend,
        "agent_model": agent_model,
    }


def write_overlay(cfg: dict[str, Any], path: Path | None = None) -> Path:
    target = path or operator_overlay_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_overlay_yaml(cfg), encoding="utf-8")
    return target


def refresh_overlay(refresh: bool = False) -> Path:
    example = toolkit_example_path()
    overlay_path = operator_overlay_path()
    if not example.is_file():
        raise FileNotFoundError(f"missing toolkit example: {example}")
    if overlay_path.is_file():
        if refresh:
            merged = deep_merge_missing(_load_raw(example), _load_raw(overlay_path))
            overlay_path.write_text(build_overlay_yaml(merged), encoding="utf-8")
        return overlay_path
    overlay = build_overlay(
        github_user=gh_user(),
        primary_clone=detect_primary_clone(toolkit_root()),
        agent_backend="claude",
    )
    return write_overlay(overlay)


def verify_prereqs(cfg: dict[str, Any]) -> None:
    proc = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError("gh not authenticated — run: gh auth login")
    from loop_agent_config import DEFAULT_CMD

    backend = str(cfg.get("agent_backend", "claude")).lower()
    configured = str(cfg.get("agent_cmd") or DEFAULT_CMD.get(backend, "claude"))
    cmd = configured if shutil.which(configured) else DEFAULT_CMD.get(backend, configured)
    if shutil.which(cmd) is None:
        raise RuntimeError(f"agent binary not found: {configured} (backend={backend})")
    verify_agent_auth(backend, cmd)


def render_launchd_plist(toolkit: Path, cfg: dict[str, Any]) -> str:
    home = str(Path.home())
    cron_script = toolkit / CRON_SCRIPT_RELATIVE
    overlay = operator_overlay_path()
    user = os.environ.get("USER", Path.home().name)

    env_lines = [
        "    <key>HOME</key>", f"    <string>{home}</string>",
        "    <key>USER</key>", f"    <string>{user}</string>",
        "    <key>PATH</key>",
        f"    <string>{home}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>",
        "    <key>PR_REVIEW_LOOP_CONFIG</key>", f"    <string>{overlay}</string>",
        "    <key>PR_REVIEW_LOOP_TOOLKIT</key>", f"    <string>{toolkit}</string>",
    ]
    ns_override = os.environ.get("KADENCE_NAMESPACE", "").strip()
    if ns_override:
        env_lines += ["    <key>KADENCE_NAMESPACE</key>", f"    <string>{ns_override}</string>"]
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if token:
        env_lines += ["    <key>CLAUDE_CODE_OAUTH_TOKEN</key>", f"    <string>{token}</string>"]
    elif api_key:
        env_lines += ["    <key>ANTHROPIC_API_KEY</key>", f"    <string>{api_key}</string>"]

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
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(LAUNCHD_PLIST)],
                   capture_output=True, text=True)
    load = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(LAUNCHD_PLIST)],
                          capture_output=True, text=True)
    if load.returncode != 0:
        load = subprocess.run(["launchctl", "load", str(LAUNCHD_PLIST)],
                              capture_output=True, text=True)
    if load.returncode != 0:
        raise RuntimeError(load.stderr.strip() or "launchctl load failed")


def uninstall_launchd() -> None:
    if not LAUNCHD_PLIST.is_file():
        return
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(LAUNCHD_PLIST)],
                   capture_output=True, text=True)
    LAUNCHD_PLIST.unlink(missing_ok=True)


def launchd_loaded() -> bool:
    return subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{LAUNCHD_LABEL}"],
        capture_output=True, text=True).returncode == 0


def install_windows_task(toolkit: Path, cfg: dict[str, Any]) -> None:
    script_path = write_windows_task_script(toolkit, cfg)
    command = render_windows_task_command(script_path)
    proc = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/F",
            "/SC",
            "MINUTE",
            "/MO",
            "15",
            "/TN",
            WINDOWS_TASK_NAME,
            "/TR",
            command,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "schtasks create failed")


def uninstall_windows_task() -> None:
    if not windows_task_loaded():
        WINDOWS_TASK_SCRIPT.unlink(missing_ok=True)
        return
    proc = subprocess.run(
        ["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "schtasks delete failed")
    WINDOWS_TASK_SCRIPT.unlink(missing_ok=True)


def windows_task_loaded() -> bool:
    return subprocess.run(
        ["schtasks", "/Query", "/TN", WINDOWS_TASK_NAME],
        capture_output=True,
        text=True,
        check=False,
    ).returncode == 0


def install_scheduler(toolkit: Path, cfg: dict[str, Any]) -> None:
    if is_windows():
        install_windows_task(toolkit, cfg)
    else:
        install_launchd(render_launchd_plist(toolkit, cfg))


def uninstall_scheduler() -> None:
    if is_windows():
        uninstall_windows_task()
    else:
        uninstall_launchd()


def scheduler_loaded() -> bool:
    if is_windows():
        return windows_task_loaded()
    return launchd_loaded()


def run_cron_now(toolkit: Path, overlay: Path) -> int:
    env = os.environ.copy()
    if overlay.is_file():
        env["PR_REVIEW_LOOP_CONFIG"] = str(overlay)
    env["PR_REVIEW_LOOP_TOOLKIT"] = str(toolkit)
    cron = toolkit / CRON_SCRIPT_RELATIVE
    if is_windows():
        return subprocess.run([resolve_bash(), str(cron)], env=env, check=False).returncode
    return subprocess.run([str(cron)], env=env, check=False).returncode


def cmd_install(args: argparse.Namespace) -> int:
    ensure_dirs()
    overlay = refresh_overlay(refresh=args.refresh_config)
    cfg = load_config(overlay)
    verify_prereqs(cfg)
    toolkit = toolkit_root()
    if not args.skip_launchd:
        install_scheduler(toolkit, cfg)
    print(f"config overlay: {overlay}")
    print(f"merged from: {toolkit_example_path()}")
    print(f"agent_backend: {cfg.get('agent_backend')}")
    if not args.skip_launchd:
        print(f"{scheduler_name()}: {scheduler_details()}")
    if args.skip_smoke:
        return 0
    return run_cron_now(toolkit, overlay)


def cmd_run(_a: argparse.Namespace) -> int:
    toolkit = toolkit_root()
    overlay = operator_overlay_path()
    return run_cron_now(toolkit, overlay)


def cmd_status(_a: argparse.Namespace) -> int:
    overlay = operator_overlay_path()
    print(f"toolkit example: {toolkit_example_path()}")
    print(f"operator overlay: {overlay} ({'exists' if overlay.is_file() else 'missing'})")
    print(f"{scheduler_name()} loaded: {scheduler_loaded()}")
    if LATEST_MD.is_file():
        print(f"\n--- {LATEST_MD} ---\n")
        print(LATEST_MD.read_text(encoding="utf-8"))
    else:
        print("\n(no firings yet — run: pr-review-loop-setup.sh run)")
    return 0


def cmd_uninstall(_a: argparse.Namespace) -> int:
    uninstall_scheduler()
    print(f"removed {scheduler_name()} job: {WINDOWS_TASK_NAME if is_windows() else LAUNCHD_LABEL}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PR review loop setup")
    sub = parser.add_subparsers(dest="command", required=True)
    p_i = sub.add_parser("install")
    p_i.add_argument("--refresh-config", action="store_true")
    p_i.add_argument("--skip-launchd", action="store_true")
    p_i.add_argument("--skip-smoke", action="store_true")
    p_i.set_defaults(func=cmd_install)
    sub.add_parser("run").set_defaults(func=cmd_run)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("uninstall").set_defaults(func=cmd_uninstall)
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
