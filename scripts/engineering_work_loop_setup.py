#!/usr/bin/env python3
"""Install and status helpers for engineering work loop cron."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from engineering_work_loop_config import (
    build_overlay_yaml,
    deep_merge_missing,
    load_config,
    operator_overlay_path,
    toolkit_example_path,
    toolkit_root,
)
from loop_registry import app_namespace
from pr_fix_config import _load_raw
from pr_fix_setup import detect_primary_clone, gh_user, verify_prereqs


# Multi-instance support. An operator can run side-by-side loops (e.g. a v2 instance
# targeting one repo/branch, alongside a default instance) by setting
# ENGINEERING_LOOP_INSTANCE. Empty = the default instance (backward compatible with v1
# identifiers). A non-empty value suffixes the launchd label, config overlay, state log,
# worktree root, and report paths so the instances never collide.
def instance_suffix() -> str:
    inst = os.environ.get("ENGINEERING_LOOP_INSTANCE", "").strip()
    return f"-{inst}" if inst else ""


def loop_name() -> str:
    """The active loop's name (the stem for label/config/state). Defaults to
    implement-loop (the former single-loop behavior)."""
    from loop_registry import resolve_loop_name

    return resolve_loop_name()


def _sfx(name: str) -> str:
    """Insert the instance suffix before a filename's extension / at its end."""
    s = instance_suffix()
    if not s:
        return name
    if "." in name:
        stem, _, ext = name.rpartition(".")
        return f"{stem}{s}.{ext}"
    return f"{name}{s}"


CRON_SCRIPT_RELATIVE = Path("scripts/engineering-work-loop-cron.sh")


def local_state_dirs() -> list[Path]:
    return [
        Path(f"~/.local/share/{app_namespace()}") / _sfx("worktrees"),
        Path(f"~/.local/share/{app_namespace()}") / _sfx(f"{loop_name()}-reports"),
    ]


def launchd_label() -> str:
    # com.<namespace>[.<inst>].<loop>, e.g. com.kadence.implement-loop,
    # com.kadence-v2.spec-loop. The loop name replaces the old hardcoded
    # 'engineering-work-loop' (which now names the family, not a concrete loop).
    s = instance_suffix()
    return f"com.{app_namespace()}{s}.{loop_name()}"


def launchd_plist() -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{launchd_label()}.plist"


def windows_task_name() -> str:
    return f"{app_namespace()}{instance_suffix()}-{loop_name()}"


def windows_task_script() -> Path:
    return Path.home() / f".local/share/{app_namespace()}" / _sfx(f"{loop_name()}-task.ps1")


def latest_md() -> Path:
    return Path.home() / f".local/share/{app_namespace()}" / _sfx(f"{loop_name()}-latest.md")


def cron_log() -> Path:
    # Per-loop (and per-instance) so the family members never clobber each other's
    # cron log, e.g. implement-loop-cron.log, spec-loop-cron-v2.log.
    return Path.home() / f".local/share/{app_namespace()}" / _sfx(f"{loop_name()}-cron.log")


def is_windows() -> bool:
    return os.name == "nt"


def scheduler_name() -> str:
    return "Task Scheduler" if is_windows() else "launchd"


def scheduler_details() -> str:
    if is_windows():
        return f"{windows_task_name()} (runs every 15 min)"
    return f"{launchd_plist()} (runs every 15 min — :00/:15/:30/:45)"


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


def _expand(path: Path) -> Path:
    return path.expanduser()


def ensure_dirs() -> None:
    _expand(Path(f"~/.config/{app_namespace()}")).mkdir(parents=True, exist_ok=True)
    for d in local_state_dirs():
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
    target.write_text(build_overlay_yaml(cfg), encoding="utf-8")
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
            overlay_path.write_text(build_overlay_yaml(merged), encoding="utf-8")
        return overlay_path

    overlay = build_overlay(
        github_user=gh_user(),
        primary_clone=detect_primary_clone(toolkit_root()),
        agent_backend="claude",
    )
    return write_overlay(overlay)


def resolve_repo_clones(cfg: dict[str, Any]) -> list[tuple[str, str, str, bool]]:
    """Return (owner, repo, clone_path, exists) for each configured repo.

    clone_path is the entry's clone_path, else git.primary_clone. exists is True
    when the resolved path is a git repository (has a .git entry).
    """
    from engineering_work_loop_config import expand_path

    primary = expand_path(str((cfg.get("git") or {}).get("primary_clone", "")))
    out: list[tuple[str, str, str, bool]] = []
    for entry in cfg.get("repos") or []:
        if not isinstance(entry, dict):
            continue
        owner = str(entry.get("owner", ""))
        repo = str(entry.get("repo", ""))
        cp = entry.get("clone_path")
        clone_path = expand_path(str(cp)) if cp else primary
        exists = bool(clone_path) and (Path(clone_path) / ".git").exists()
        out.append((owner, repo, clone_path, exists))
    return out


def render_windows_task_script(toolkit: Path, cfg: dict[str, Any]) -> str:
    overlay = operator_overlay_path()
    cron_script = toolkit / CRON_SCRIPT_RELATIVE
    home = str(Path.home())
    bash = resolve_bash()
    lines = [
        "$env:HOME=" + _ps_quote(home),
        "$env:USERPROFILE=" + _ps_quote(home),
        "$env:ENGINEERING_LOOP_CONFIG=" + _ps_quote(str(overlay)),
        "$env:ENGINEERING_LOOP_TOOLKIT=" + _ps_quote(str(toolkit)),
    ]

    # Parity with the launchd plist: namespace override, instance, loop name + prompt,
    # and base ref so a Windows Task Scheduler install runs the same family loop against
    # the same branch and namespace.
    ns_override = os.environ.get("KADENCE_NAMESPACE", "").strip()
    if ns_override:
        lines.append("$env:KADENCE_NAMESPACE=" + _ps_quote(ns_override))
    inst = os.environ.get("ENGINEERING_LOOP_INSTANCE", "").strip()
    if inst:
        lines.append("$env:ENGINEERING_LOOP_INSTANCE=" + _ps_quote(inst))

    from loop_registry import get_loop

    desc = get_loop(loop_name())
    lines.append("$env:ENGINEERING_LOOP_NAME=" + _ps_quote(desc.name))
    prompt = (
        str((cfg.get("loop") or {}).get("prompt", "")).strip()
        or os.environ.get("ENGINEERING_LOOP_PROMPT", "").strip()
        or desc.prompt
    )
    lines.append("$env:ENGINEERING_LOOP_PROMPT=" + _ps_quote(prompt))

    base_ref = (
        str((cfg.get("git") or {}).get("base_ref", "")).strip()
        or os.environ.get("ENGINEERING_LOOP_BASE_REF", "").strip()
    )
    if base_ref:
        lines.append("$env:ENGINEERING_LOOP_BASE_REF=" + _ps_quote(base_ref))

    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if token:
        lines.append("$env:CLAUDE_CODE_OAUTH_TOKEN=" + _ps_quote(token))
    elif api_key:
        lines.append("$env:ANTHROPIC_API_KEY=" + _ps_quote(api_key))

    lines.append("& " + _ps_quote(bash) + " " + _ps_quote(str(cron_script)))
    return "\n".join(lines) + "\n"


def write_windows_task_script(toolkit: Path, cfg: dict[str, Any]) -> Path:
    windows_task_script().parent.mkdir(parents=True, exist_ok=True)
    windows_task_script().write_text(render_windows_task_script(toolkit, cfg), encoding="utf-8")
    return windows_task_script()


def render_windows_task_command(script_path: Path) -> str:
    return (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        f'"{script_path}"'
    )


def render_launchd_plist(toolkit: Path, cfg: dict[str, Any]) -> str:
    home = str(Path.home())
    cron_script = toolkit / CRON_SCRIPT_RELATIVE
    overlay = operator_overlay_path()
    user = os.environ.get("USER", Path.home().name)

    env_lines = [
        "    <key>HOME</key>",
        f"    <string>{home}</string>",
        "    <key>USER</key>",
        f"    <string>{user}</string>",
        "    <key>PATH</key>",
        f"    <string>{home}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>",
        "    <key>ENGINEERING_LOOP_CONFIG</key>",
        f"    <string>{overlay}</string>",
        "    <key>ENGINEERING_LOOP_TOOLKIT</key>",
        f"    <string>{toolkit}</string>",
    ]
    # Namespace override — only when set, so the cron'd loop resolves the same
    # config/state/label namespace as install time (default 'kadence' needs nothing).
    ns_override = os.environ.get("KADENCE_NAMESPACE", "").strip()
    if ns_override:
        env_lines += [
            "    <key>KADENCE_NAMESPACE</key>",
            f"    <string>{ns_override}</string>",
        ]
    # Instance name — so the cron'd loop resolves its own instance-suffixed config/state.
    inst = os.environ.get("ENGINEERING_LOOP_INSTANCE", "").strip()
    if inst:
        env_lines += [
            "    <key>ENGINEERING_LOOP_INSTANCE</key>",
            f"    <string>{inst}</string>",
        ]
    # Loop name — which family member this cron runs (implement-loop, spec-loop, ...).
    # Drives the config/label/state stem and selects the descriptor's prompt + skill.
    from loop_registry import get_loop

    desc = get_loop(loop_name())
    env_lines += [
        "    <key>ENGINEERING_LOOP_NAME</key>",
        f"    <string>{desc.name}</string>",
    ]
    # Prompt — the loop descriptor's prompt by default; an explicit config `loop.prompt`
    # or ENGINEERING_LOOP_PROMPT overrides. A bare filename resolves under the toolkit's
    # .github/prompts/.
    prompt = (
        str((cfg.get("loop") or {}).get("prompt", "")).strip()
        or os.environ.get("ENGINEERING_LOOP_PROMPT", "").strip()
        or desc.prompt
    )
    env_lines += [
        "    <key>ENGINEERING_LOOP_PROMPT</key>",
        f"    <string>{prompt}</string>",
    ]
    # Base ref — the worktree forks from this branch (e.g. origin/phase2), not main.
    # Read from config (git.base_ref) or env; only emit when set.
    base_ref = (
        str((cfg.get("git") or {}).get("base_ref", "")).strip()
        or os.environ.get("ENGINEERING_LOOP_BASE_REF", "").strip()
    )
    if base_ref:
        env_lines += [
            "    <key>ENGINEERING_LOOP_BASE_REF</key>",
            f"    <string>{base_ref}</string>",
        ]
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
  <string>{launchd_label()}</string>
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
  <string>{cron_log()}</string>
  <key>StandardErrorPath</key>
  <string>{cron_log()}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
"""


def install_launchd(plist_text: str) -> None:
    launchd_plist().parent.mkdir(parents=True, exist_ok=True)
    launchd_plist().write_text(plist_text, encoding="utf-8")
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(launchd_plist())],
        capture_output=True,
        text=True,
    )
    load = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(launchd_plist())],
        capture_output=True,
        text=True,
    )
    if load.returncode != 0:
        load = subprocess.run(
            ["launchctl", "load", str(launchd_plist())],
            capture_output=True,
            text=True,
        )
    if load.returncode != 0:
        raise RuntimeError(load.stderr.strip() or "launchctl load failed")


def uninstall_launchd() -> None:
    if not launchd_plist().is_file():
        return
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(launchd_plist())],
        capture_output=True,
        text=True,
    )
    launchd_plist().unlink(missing_ok=True)


def launchd_loaded() -> bool:
    proc = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{launchd_label()}"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


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
            windows_task_name(),
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
        windows_task_script().unlink(missing_ok=True)
        return
    proc = subprocess.run(
        ["schtasks", "/Delete", "/TN", windows_task_name(), "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "schtasks delete failed")
    windows_task_script().unlink(missing_ok=True)


def windows_task_loaded() -> bool:
    return subprocess.run(
        ["schtasks", "/Query", "/TN", windows_task_name()],
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
        env["ENGINEERING_LOOP_CONFIG"] = str(overlay)
    env["ENGINEERING_LOOP_TOOLKIT"] = str(toolkit)
    cron = toolkit / CRON_SCRIPT_RELATIVE
    if is_windows():
        proc = subprocess.run([resolve_bash(), str(cron)], env=env, check=False)
    else:
        proc = subprocess.run([str(cron)], env=env, check=False)
    if latest_md().is_file():
        print(f"\n--- last status ({latest_md()}) ---")
        print(latest_md().read_text(encoding="utf-8"))
    return proc.returncode


def cmd_install(args: argparse.Namespace) -> int:
    ensure_dirs()
    overlay = refresh_overlay(refresh=args.refresh_config)
    cfg = load_config(overlay)
    verify_prereqs(cfg)

    clones = resolve_repo_clones(cfg)
    missing = [(o, r, cp) for (o, r, cp, exists) in clones if not exists]
    if clones and len(missing) == len(clones):
        raise RuntimeError(
            "no configured repo has a valid local clone; set clone_path per repo "
            "or git.primary_clone in "
            f"{toolkit_example_path()} / {overlay}"
        )

    toolkit = toolkit_root()
    if not args.skip_launchd:
        install_scheduler(toolkit, cfg)

    print(f"config overlay: {overlay}")
    print(f"merged from: {toolkit_example_path()}")
    print(f"primary clone (fallback): {cfg.get('git', {}).get('primary_clone')}")
    print("repo clones:")
    for owner, repo, clone_path, exists in clones:
        mark = "ok" if exists else "MISSING"
        print(f"  - {owner}/{repo} -> {clone_path} [{mark}]")
    if missing:
        print(
            f"warning: {len(missing)} repo clone(s) missing; issues in those repos "
            "will be skipped until cloned."
        )
    print(f"agent_backend: {cfg.get('agent_backend')}")
    if not args.skip_launchd:
        print(f"{scheduler_name()}: {scheduler_details()}")
        if not is_windows():
            print(f"cron log: {cron_log()}")

    if args.skip_smoke:
        return 0

    return run_cron_now(toolkit, overlay)


def cmd_run(_args: argparse.Namespace) -> int:
    toolkit = toolkit_root()
    overlay = operator_overlay_path()
    return run_cron_now(toolkit, overlay)


def cmd_status(_args: argparse.Namespace) -> int:
    overlay = operator_overlay_path()
    example = toolkit_example_path()
    print(f"toolkit example: {example}")
    print(f"operator overlay: {overlay} ({'exists' if overlay.is_file() else 'missing'})")
    print(f"{scheduler_name()} loaded: {scheduler_loaded()}")
    print(f"local state: ~/.local/share/{app_namespace()}/")
    if latest_md().is_file():
        print(f"\n--- {latest_md()} ---\n")
        print(latest_md().read_text(encoding="utf-8"))
    else:
        print("\n(no firings yet — run: engineering-work-loop-setup.sh run)")
    return 0


def cmd_uninstall(_args: argparse.Namespace) -> int:
    uninstall_scheduler()
    job = windows_task_name() if is_windows() else launchd_label()
    print(f"removed {scheduler_name()} job: {job}")
    return 0


def main() -> int:
    from loop_registry import ENGINE_DRIVEN, resolve_loop_name

    parser = argparse.ArgumentParser(description="Engineering work loop family setup")
    # --loop selects which family member to install (implement-loop | spec-loop).
    # It sets ENGINEERING_LOOP_NAME for the whole run so label/config/state/prompt
    # derive from that loop. Default = implement-loop (the former single loop).
    parser.add_argument(
        "--loop",
        choices=list(ENGINE_DRIVEN),
        default=None,
        help="which engine-driven family loop to install (default: implement-loop). "
        "pr-review-loop / pr-comment-fix-loop have their own setup scripts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="dirs, config overlay, scheduler, smoke test")
    p_install.add_argument("--refresh-config", action="store_true")
    p_install.add_argument("--skip-launchd", action="store_true")
    p_install.add_argument("--skip-smoke", action="store_true")
    p_install.set_defaults(func=cmd_install)

    p_run = sub.add_parser("run", help="run one cron firing now")
    p_run.set_defaults(func=cmd_run)

    p_status = sub.add_parser("status", help="show paths and last firing")
    p_status.set_defaults(func=cmd_status)

    p_uninstall = sub.add_parser("uninstall", help="remove scheduler job")
    p_uninstall.set_defaults(func=cmd_uninstall)

    args = parser.parse_args()
    # --loop wins over an ambient ENGINEERING_LOOP_NAME so `--loop spec-loop` is
    # unambiguous; the resolved name flows to every loop-aware derivation via env.
    if args.loop:
        os.environ["ENGINEERING_LOOP_NAME"] = args.loop
    else:
        os.environ["ENGINEERING_LOOP_NAME"] = resolve_loop_name(
            os.environ.get("ENGINEERING_LOOP_NAME")
        )
    try:
        return int(args.func(args))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
