#!/usr/bin/env python3
"""Verify Loop AC by running verify commands from issue body."""
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AcItem:
    id: str
    description: str
    verify_cmd: str | None
    checked: bool


# Auto tier: block shell injection. Single argv-style commands only — no pipes,
# redirects, command substitution, or chaining. Compound checks must go through
# loop_check.py (allowlisted below), not shell pipelines.
_FORBIDDEN_AUTO = re.compile(r"[;`$|<>]|&&")
DEFAULT_ALLOWED_AUTO_PREFIXES: tuple[str, ...] = (
    "test ",
    "grep ",
    "gh issue view",
    "gh pr checks",
    "gh api ",
    "python3 scripts/loop_check.py",
    "git diff",
    "git -C ",
    "git rev-parse",
)


def parse_loop_ac(body: str) -> list[AcItem]:
    items: list[AcItem] = []
    section = re.search(r"## Loop AC\s*(.*?)(?:\n## |\Z)", body, re.S | re.I)
    if not section:
        return items
    text = section.group(1)
    pattern = re.compile(
        r"- \[( |x)\] (AC-\d+):\s*(.+?)(?:\n\s*- verify:\s*`([^`]+)`|\n(?=- \[ |$))",
        re.S,
    )
    for m in pattern.finditer(text):
        items.append(
            AcItem(
                id=m.group(2),
                description=m.group(3).strip(),
                verify_cmd=m.group(4),
                checked=m.group(1).lower() == "x",
            )
        )
    return items


def is_auto_command_allowed(
    cmd: str,
    allowed_prefixes: tuple[str, ...] | list[str] | None = None,
) -> tuple[bool, str]:
    prefixes = tuple(allowed_prefixes or DEFAULT_ALLOWED_AUTO_PREFIXES)
    cmd = cmd.strip()
    if not cmd:
        return False, "empty command"
    if _FORBIDDEN_AUTO.search(cmd):
        return False, "forbidden shell metacharacters in auto tier"
    if not any(cmd.startswith(prefix) for prefix in prefixes):
        return False, "command not on auto-tier allowlist"
    return True, ""


def load_allowed_prefixes_from_config(config_path: str) -> list[str]:
    """Load verify.auto_allowed_prefixes from loop config YAML (no PyYAML)."""
    prefixes: list[str] = []
    in_verify = False
    in_list = False
    for line in Path(config_path).read_text().splitlines():
        if re.match(r"^verify:\s*$", line):
            in_verify = True
            in_list = False
            continue
        if in_verify and line and not line.startswith(" "):
            break
        if in_verify and re.match(r"^\s+auto_allowed_prefixes:\s*$", line):
            in_list = True
            continue
        if in_list:
            m = re.match(r'^\s+-\s+["\']?(.+?)["\']?\s*$', line)
            if m:
                prefixes.append(m.group(1))
            elif line.strip():
                break
    return prefixes


def resolve_toolkit_scripts(cmd: str) -> str:
    """Rewrite `scripts/loop_check.py` → the TOOLKIT install's absolute path.

    v2 independence: verify commands are authored portably as `python3
    scripts/loop_check.py …`, but they run in the TARGET repo's worktree cwd — which
    does not contain the toolkit. When ENGINEERING_LOOP_TOOLKIT is set, rewrite the
    toolkit-owned `scripts/<name>` reference to `<toolkit>/scripts/<name>` so the
    real install is invoked, with no vendored/symlinked toolkit needed in the target.
    """
    toolkit = os.environ.get("ENGINEERING_LOOP_TOOLKIT", "").strip()
    if not toolkit:
        return cmd
    base = os.path.expanduser(toolkit)
    # Only rewrite the loop's own helper scripts (not arbitrary 'scripts/' in the repo).
    for name in ("loop_check.py",):
        cmd = cmd.replace(f"scripts/{name}", f"{base}/scripts/{name}")
    return cmd


def run_verify(cmd: str, cwd: str | None, *, use_shell: bool) -> tuple[bool, str]:
    # use_shell=False uses shlex.split + subprocess without shell expansion.
    # Wired via --strict-no-shell for operators who want argv-only execution;
    # default auto tier keeps shell=True for pipelines (grep | …) in verify cmds.
    cmd = resolve_toolkit_scripts(cmd)
    try:
        if use_shell:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        else:
            proc = subprocess.run(
                shlex.split(cmd),
                shell=False,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out.strip()[:500]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except (OSError, ValueError) as exc:
        return False, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Loop AC commands")
    parser.add_argument("--body-file", type=argparse.FileType("r"), required=True)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--require-all", action="store_true")
    parser.add_argument(
        "--risk-tier",
        choices=("auto", "assist", "human-only"),
        default="assist",
        help="auto enforces command allowlist; assist requires --allow-assist-shell",
    )
    parser.add_argument(
        "--allow-assist-shell",
        action="store_true",
        help="Required for assist tier when running author-provided verify commands",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help=(
            "v2 anti-reward-hack mode: every AC MUST carry a verify command the "
            "harness runs (a missing command FAILs, never skips); assist-tier "
            "commands are run (implies --allow-assist-shell); the agent's [x] is "
            "advisory — only the harness exit code counts."
        ),
    )
    parser.add_argument(
        "--config",
        help="Loop config YAML; loads verify.auto_allowed_prefixes when set",
    )
    parser.add_argument(
        "--strict-no-shell",
        action="store_true",
        help="Run verify commands via shlex argv (no shell expansion); pipelines unsupported",
    )
    args = parser.parse_args()

    allowed_prefixes: tuple[str, ...] | None = None
    if args.config:
        loaded = load_allowed_prefixes_from_config(args.config)
        if loaded:
            allowed_prefixes = tuple(loaded)

    body = args.body_file.read()
    items = parse_loop_ac(body)
    if not items:
        print("no Loop AC items found", file=sys.stderr)
        sys.exit(2)

    failed = 0
    skipped = 0
    for item in items:
        if not item.verify_cmd:
            # (v2 --enforce) An AC with no verify command cannot be trusted — the
            # agent's [x] is not evidence. Fail it rather than skip, so an item can't
            # pass by simply omitting a command.
            if args.enforce:
                print(f"{item.id}: FAIL (no verify command — required under --enforce)")
                failed += 1
                continue
            print(f"{item.id}: SKIP (no verify command)")
            if args.require_all:
                skipped += 1
            continue

        if args.risk_tier == "auto":
            ok_allowed, reason = is_auto_command_allowed(
                item.verify_cmd, allowed_prefixes
            )
            if not ok_allowed:
                print(f"{item.id}: BLOCKED — {reason}")
                failed += 1
                continue
            use_shell = not args.strict_no_shell
        elif args.risk_tier == "assist":
            # (v2 --enforce) run the command rather than skip — the checkbox never
            # substitutes for evidence. --enforce implies --allow-assist-shell.
            if not (args.allow_assist_shell or args.enforce):
                print(f"{item.id}: SKIP (assist tier; pass --allow-assist-shell)")
                skipped += 1
                continue
            use_shell = True
        else:
            # human-only: genuinely needs a human. Under --enforce this is a FAIL
            # (the loop cannot self-certify it), not a silent skip.
            if args.enforce:
                print(f"{item.id}: FAIL (human-only tier — requires human sign-off)")
                failed += 1
                continue
            print(f"{item.id}: SKIP (human-only tier)")
            skipped += 1
            continue

        ok, out = run_verify(item.verify_cmd, args.cwd, use_shell=use_shell)
        status = "PASS" if ok else "FAIL"
        box = "checked" if item.checked else "unchecked"
        print(f"{item.id}: {status} ({box}) — {item.description[:60]}")
        if out:
            print(f"  output: {out[:200]}")
        if not ok:
            failed += 1

    if args.require_all and skipped:
        print(f"{skipped} AC item(s) skipped under --require-all", file=sys.stderr)
        sys.exit(1)
    if failed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
