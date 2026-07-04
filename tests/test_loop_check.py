"""Tests for loop_check.py argv-only verify helpers."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

LOOP_CHECK = Path(__file__).resolve().parents[1] / "scripts" / "loop_check.py"


def _run(args, cwd):
    return subprocess.run(
        [sys.executable, str(LOOP_CHECK), "--cwd", str(cwd), *args],
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("a\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)


# (v2) md-status-done / sync-status-mentions / issue-has-milestone removed — those
# were the M18 markdown-status-drift and epic_milestone verifiers. No duplicated
# status ⇒ nothing to verify. The changed-files-max / changed-lines-max diff-size
# tripwire is also removed — feature sizing is a generation-time reasoning judgment,
# not a mechanical gate, and Loop AC verifies BEHAVIOR only. See
# assessments/kadence-v2.


def test_cmd_succeeds_on_passing_command(tmp_path):
    assert _run(["cmd-succeeds", f"{sys.executable} -c pass"], tmp_path).returncode == 0


def test_cmd_succeeds_on_failing_command(tmp_path):
    r = _run(["cmd-succeeds", f"{sys.executable} -c \"import sys; sys.exit(3)\""], tmp_path)
    assert r.returncode == 1


def test_cmd_fails_on_failing_command(tmp_path):
    r = _run(["cmd-fails", f"{sys.executable} -c \"import sys; sys.exit(3)\""], tmp_path)
    assert r.returncode == 0


def test_cmd_fails_on_passing_command(tmp_path):
    assert _run(["cmd-fails", f"{sys.executable} -c pass"], tmp_path).returncode == 1


def test_cmd_succeeds_is_no_shell(tmp_path):
    # A shell metachar in the inner command must NOT be interpreted by a shell:
    # the redirect target must not be created; the command is argv-split only.
    target = tmp_path / "should_not_exist"
    _run(["cmd-succeeds", f"echo pwned > {target}"], tmp_path)
    assert not target.exists()


def test_cmd_succeeds_empty_inner_is_failure(tmp_path):
    assert _run(["cmd-succeeds", ""], tmp_path).returncode == 1
