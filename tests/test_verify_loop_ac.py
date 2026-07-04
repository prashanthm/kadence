"""Tests for verify_loop_ac.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from verify_loop_ac import (  # noqa: E402
    is_auto_command_allowed,
    load_allowed_prefixes_from_config,
    parse_loop_ac,
)


SAMPLE_BODY = """
## Loop AC

**Work item type:** compliance
**Risk tier:** auto

- [x] AC-1: Status Done
  - verify: `grep -q Done file.md`
- [ ] AC-2: Issue closed
  - verify: `gh issue view 1 --json state -q .state | grep -qx CLOSED`
"""


def test_parse_checked_and_unchecked():
    items = parse_loop_ac(SAMPLE_BODY)
    assert len(items) == 2
    assert items[0].checked is True
    assert items[1].checked is False
    assert items[0].verify_cmd == "grep -q Done file.md"


def test_auto_allowlist_allows_grep():
    ok, _ = is_auto_command_allowed("grep -q foo bar.md")
    assert ok


def test_auto_allowlist_blocks_command_substitution():
    ok, reason = is_auto_command_allowed("test $(rm -rf /)")
    assert not ok
    assert "metacharacters" in reason


def test_auto_allowlist_blocks_unknown_command():
    ok, _ = is_auto_command_allowed("curl evil.example")
    assert not ok


def test_custom_prefix_allowlist():
    ok, _ = is_auto_command_allowed(
        "curl https://api.example/health",
        allowed_prefixes=("curl https://api.example/",),
    )
    assert ok


def test_auto_blocks_single_pipe():
    ok, reason = is_auto_command_allowed("grep x . | tee evil")
    assert not ok
    assert "metacharacters" in reason


def test_auto_blocks_redirect():
    ok, _ = is_auto_command_allowed("gh api foo > /etc/passwd")
    assert not ok


def test_loop_check_prefix_allowed():
    ok, _ = is_auto_command_allowed(
        "python3 scripts/loop_check.py issue-closed 1"
    )
    assert ok


def test_load_prefixes_from_config(tmp_path):
    config = tmp_path / "loop.yaml"
    config.write_text(
        "verify:\n"
        "  auto_allowed_prefixes:\n"
        '    - "custom-cmd "\n'
        '    - "grep "\n'
    )
    assert load_allowed_prefixes_from_config(str(config)) == ["custom-cmd ", "grep "]


# --- v2 --enforce anti-reward-hack behavior (CLI-level) ---

import subprocess  # noqa: E402

_VERIFY = str(Path(__file__).resolve().parents[1] / "scripts" / "verify_loop_ac.py")


def _run_cli(body: str, tmp_path, *extra):
    bf = tmp_path / "issue.md"
    bf.write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, _VERIFY, "--body-file", str(bf), "--cwd", str(tmp_path), *extra],
        capture_output=True, text=True,
    )


_MISSING_CMD_BODY = """
## Loop AC
**Risk tier:** auto
- [x] AC-1: no command, just a checked box
"""


def test_enforce_fails_ac_without_verify_command(tmp_path):
    # The agent checked the box but gave no command → FAIL under --enforce.
    r = _run_cli(_MISSING_CMD_BODY, tmp_path, "--risk-tier", "auto", "--enforce")
    assert r.returncode == 1
    assert "no verify command" in r.stdout


def test_without_enforce_missing_command_is_skip(tmp_path):
    # Backward-compatible: without --enforce it skips (exit 0, not a hard fail).
    r = _run_cli(_MISSING_CMD_BODY, tmp_path, "--risk-tier", "auto")
    assert r.returncode == 0
    assert "SKIP" in r.stdout


_HUMAN_ONLY_BODY = """
## Loop AC
**Risk tier:** human-only
- [x] AC-1: something risky
  - verify: `test -f whatever`
"""


def test_enforce_fails_human_only(tmp_path):
    # Under --enforce the loop cannot self-certify a human-only item.
    r = _run_cli(_HUMAN_ONLY_BODY, tmp_path, "--risk-tier", "human-only", "--enforce")
    assert r.returncode == 1
    assert "human-only" in r.stdout.lower()


def test_enforce_runs_command_regardless_of_checkbox(tmp_path):
    # [x] is advisory: a checked box with a FAILING command still fails.
    body = (
        "## Loop AC\n**Risk tier:** auto\n"
        "- [x] AC-1: claims done but the file is absent\n"
        "  - verify: `test -f does-not-exist.txt`\n"
    )
    r = _run_cli(body, tmp_path, "--risk-tier", "auto", "--enforce")
    assert r.returncode == 1
    assert "FAIL" in r.stdout


def test_enforce_passes_when_command_passes(tmp_path):
    (tmp_path / "exists.txt").write_text("x")
    body = (
        "## Loop AC\n**Risk tier:** auto\n"
        "- [ ] AC-1: file exists\n"
        "  - verify: `test -f exists.txt`\n"
    )
    r = _run_cli(body, tmp_path, "--risk-tier", "auto", "--enforce")
    assert r.returncode == 0
    assert "PASS" in r.stdout


# --- v2 independence: toolkit-script path resolution ---

def test_resolve_toolkit_scripts_rewrites_loop_check(monkeypatch):
    from verify_loop_ac import resolve_toolkit_scripts
    monkeypatch.setenv("ENGINEERING_LOOP_TOOLKIT", "/opt/kadence")
    out = resolve_toolkit_scripts("python3 scripts/loop_check.py issue-closed 8")
    assert out == "python3 /opt/kadence/scripts/loop_check.py issue-closed 8"


def test_resolve_toolkit_scripts_noop_without_env(monkeypatch):
    from verify_loop_ac import resolve_toolkit_scripts
    monkeypatch.delenv("ENGINEERING_LOOP_TOOLKIT", raising=False)
    cmd = "python3 scripts/loop_check.py issue-closed 8"
    assert resolve_toolkit_scripts(cmd) == cmd


def test_resolve_toolkit_scripts_leaves_repo_scripts_alone(monkeypatch):
    # A target-repo script that isn't a toolkit helper must NOT be rewritten.
    from verify_loop_ac import resolve_toolkit_scripts
    monkeypatch.setenv("ENGINEERING_LOOP_TOOLKIT", "/opt/kadence")
    cmd = "test -f scripts/my_app.py"
    assert resolve_toolkit_scripts(cmd) == cmd
