"""Tests for engineering_work_loop setup helpers."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import engineering_work_loop_setup as setup  # noqa: E402
from engineering_work_loop_config import (  # noqa: E402
    _normalize_config,
    load_config,
    toolkit_root,
)
from engineering_work_loop_setup import (  # noqa: E402
    build_overlay,
    launchd_label,
    render_launchd_plist,
    resolve_bash,
    resolve_repo_clones,
    windows_task_name,
)

EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "skills/engineering-work-loop/config.example.yaml"
)


def test_max_items_caps_clamped():
    # negative/zero clamp up to 1; runaway clamps down to 100; invalid -> default
    assert _normalize_config({"max_items_per_repo": -5})["max_items_per_repo"] == 1
    assert _normalize_config({"max_items_per_repo": 0})["max_items_per_repo"] == 1
    assert _normalize_config({"max_items_per_repo": 500})["max_items_per_repo"] == 100
    assert _normalize_config({"max_items_per_repo": "x"})["max_items_per_repo"] == 5
    assert _normalize_config({"max_items_per_repo": 5})["max_items_per_repo"] == 5
    # legacy global ceiling clamped too, only when present
    assert _normalize_config({"max_items_per_firing": 999})["max_items_per_firing"] == 100
    assert _normalize_config({}).get("max_items_per_firing") is None


def test_build_overlay_shape():
    cfg = build_overlay(
        github_user="alice",
        primary_clone="/tmp/repo",
        agent_backend="copilot",
    )
    assert cfg["github_user"] == "alice"
    assert cfg["git"]["primary_clone"] == "/tmp/repo"
    assert cfg["agent_backend"] == "copilot"


def test_render_launchd_plist_includes_paths():
    toolkit = toolkit_root()
    plist = render_launchd_plist(
        toolkit,
        {"agent_backend": "cursor"},
    )
    assert launchd_label() == "com.ai-sdlc.implement-loop"
    assert "engineering-work-loop-cron.sh" in plist
    assert "ENGINEERING_LOOP_CONFIG" in plist
    assert "ENGINEERING_LOOP_TOOLKIT" in plist
    assert "HOME" in plist
    # every 15 min: :00/:15/:30/:45
    for minute in ("0", "15", "30", "45"):
        assert f"<integer>{minute}</integer>" in plist


def test_render_windows_task_script_includes_env(monkeypatch, tmp_path):
    git_bash = tmp_path / "Git" / "bin" / "bash.exe"
    git_bash.parent.mkdir(parents=True)
    git_bash.write_text("")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setenv("CURSOR_API_KEY", "cursor-key")
    monkeypatch.setattr(setup.shutil, "which", lambda name: None)

    script = setup.render_windows_task_script(toolkit_root(), load_config(EXAMPLE))

    assert "ENGINEERING_LOOP_CONFIG" in script
    assert "ENGINEERING_LOOP_TOOLKIT" in script
    assert "CURSOR_API_KEY" in script
    assert "engineering-work-loop-cron.sh" in script
    assert str(git_bash) in script
    # loop name + prompt injected (parity with the launchd plist); default loop.
    assert "ENGINEERING_LOOP_NAME" in script and "implement-loop" in script
    assert "ENGINEERING_LOOP_PROMPT" in script and "implement-loop.prompt.md" in script


def test_render_windows_task_script_honors_loop_and_base_ref(monkeypatch, tmp_path):
    git_bash = tmp_path / "Git" / "bin" / "bash.exe"
    git_bash.parent.mkdir(parents=True)
    git_bash.write_text("")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setattr(setup.shutil, "which", lambda name: None)
    monkeypatch.setenv("ENGINEERING_LOOP_NAME", "spec-loop")
    monkeypatch.setenv("ENGINEERING_LOOP_INSTANCE", "v2")

    script = setup.render_windows_task_script(
        toolkit_root(), {"agent_backend": "claude", "git": {"base_ref": "origin/phase2"}}
    )
    assert "ENGINEERING_LOOP_NAME" in script and "spec-loop" in script
    assert "ENGINEERING_LOOP_PROMPT" in script and "spec-loop.prompt.md" in script
    assert "ENGINEERING_LOOP_INSTANCE" in script and "v2" in script
    assert "ENGINEERING_LOOP_BASE_REF" in script and "origin/phase2" in script


def test_render_windows_task_command_uses_powershell_file_invocation(tmp_path):
    script_path = tmp_path / "engineering-work-loop-task.ps1"

    cmd = setup.render_windows_task_command(script_path)

    assert cmd.startswith('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "')
    assert cmd.endswith(f'{script_path}"')


def test_render_windows_task_command_stays_under_schtasks_limit(monkeypatch):
    long_home = "C:/Users/operator-with-a-very-long-profile-name"
    script_path = Path(long_home) / ".local/share/ai-sdlc/engineering-work-loop-task.ps1"
    cmd = setup.render_windows_task_command(script_path)
    assert len(cmd) < 261


def test_resolve_bash_prefers_git_bash_over_system32(monkeypatch, tmp_path):
    git_bash = tmp_path / "Git" / "bin" / "bash.exe"
    git_bash.parent.mkdir(parents=True)
    git_bash.write_text("")
    system32_bash = tmp_path / "Windows" / "System32" / "bash.exe"
    system32_bash.parent.mkdir(parents=True)
    system32_bash.write_text("")

    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setattr(setup.shutil, "which", lambda name: str(system32_bash))

    assert resolve_bash() == str(git_bash)


def test_install_windows_task_registers_schtasks(monkeypatch, tmp_path):
    git_bash = tmp_path / "Git" / "bin" / "bash.exe"
    git_bash.parent.mkdir(parents=True)
    git_bash.write_text("")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setattr(setup.shutil, "which", lambda name: None)

    script_path = tmp_path / "engineering-work-loop-task.ps1"
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    monkeypatch.setattr(
        setup,
        "write_windows_task_script",
        lambda toolkit, cfg: script_path,
    )

    setup.install_windows_task(toolkit_root(), load_config(EXAMPLE))

    assert len(calls) == 1
    assert calls[0][:2] == ["schtasks", "/Create"]
    assert calls[0][calls[0].index("/SC") + 1] == "MINUTE"
    assert calls[0][calls[0].index("/MO") + 1] == "15"
    assert setup.windows_task_name() in calls[0]
    tr = calls[0][calls[0].index("/TR") + 1]
    assert str(script_path) in tr


def test_uninstall_windows_task_deletes_schtasks(monkeypatch, tmp_path):
    script_path = tmp_path / "engineering-work-loop-task.ps1"
    script_path.write_text("task", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        return R()

    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    monkeypatch.setattr(setup, "windows_task_loaded", lambda: True)
    monkeypatch.setattr(setup, "windows_task_script", lambda: script_path)

    setup.uninstall_windows_task()

    assert calls == [["schtasks", "/Delete", "/TN", setup.windows_task_name(), "/F"]]
    assert not script_path.exists()


def test_install_scheduler_dispatches_by_platform(monkeypatch):
    seen: list[str] = []

    monkeypatch.setattr(setup, "install_windows_task", lambda toolkit, cfg: seen.append("windows"))
    monkeypatch.setattr(setup, "install_launchd", lambda plist: seen.append("launchd"))
    monkeypatch.setattr(setup, "render_launchd_plist", lambda t, c: "plist")

    cfg = load_config(EXAMPLE)
    toolkit = toolkit_root()

    monkeypatch.setattr(setup, "is_windows", lambda: True)
    setup.install_scheduler(toolkit, cfg)
    assert seen == ["windows"]

    seen.clear()
    monkeypatch.setattr(setup, "is_windows", lambda: False)
    setup.install_scheduler(toolkit, cfg)
    assert seen == ["launchd"]


def test_scheduler_name_platform_specific(monkeypatch):
    monkeypatch.setattr(setup, "is_windows", lambda: True)
    assert setup.scheduler_name() == "Task Scheduler"
    monkeypatch.setattr(setup, "is_windows", lambda: False)
    assert setup.scheduler_name() == "launchd"


def test_cron_wrapper_skips_when_locked(tmp_path):
    """A pre-existing lock dir makes the cron wrapper skip (exit 0) before any work."""
    import subprocess

    wrapper = (
        Path(__file__).resolve().parents[1] / "scripts" / "engineering-work-loop-cron.sh"
    )
    lock_dir = tmp_path / "held.lock"
    lock_dir.mkdir()
    proc = subprocess.run(
        [resolve_bash(), str(wrapper)],
        env={
            **os.environ,
            "ENGINEERING_LOOP_LOCK_DIR": str(lock_dir),
            "ENGINEERING_LOOP_LOCK_STALE_MIN": "120",
        },
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "skip" in (proc.stdout + proc.stderr).lower()
    assert lock_dir.is_dir()


def _extract_lock_preamble(wrapper: Path) -> str:
    """Pull the lock block (through `echo $$ > .../pid`) out of a cron wrapper so
    the lock logic can be exercised without running a full firing."""
    text = wrapper.read_text().splitlines()
    start = next(i for i, ln in enumerate(text) if "Single-instance lock" in ln)
    end = next(i for i, ln in enumerate(text) if '/pid"' in ln and "echo" in ln)
    body = "\n".join(text[start : end + 1])
    return "set -euo pipefail\n" + body + '\necho "ACQUIRED"\n'


def test_cron_wrapper_reaps_orphaned_lock(tmp_path):
    """A lock owned by a dead PID is reaped immediately (not skipped)."""
    import subprocess

    wrapper = (
        Path(__file__).resolve().parents[1] / "scripts" / "engineering-work-loop-cron.sh"
    )
    harness = _extract_lock_preamble(wrapper)
    lock_dir = tmp_path / "orphan.lock"
    lock_dir.mkdir()
    (lock_dir / "pid").write_text("99999")  # a PID that is not alive
    proc = subprocess.run(
        [resolve_bash(), "-c", harness],
        env={**os.environ, "ENGINEERING_LOOP_LOCK_DIR": str(lock_dir)},
        capture_output=True,
        text=True,
    )
    combined = proc.stdout + proc.stderr
    assert "reaping orphaned lock" in combined
    assert "ACQUIRED" in combined  # proceeded past the lock
    assert "skip: previous" not in combined


def test_cron_wrapper_syntax():
    import subprocess

    wrapper = (
        Path(__file__).resolve().parents[1] / "scripts" / "engineering-work-loop-cron.sh"
    )
    proc = subprocess.run([resolve_bash(), "-n", str(wrapper)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_load_config_merges_status_defaults(tmp_path, monkeypatch):
    example = tmp_path / "example.yaml"
    example.write_text(
        "github_user: bob\n"
        "git:\n"
        "  primary_clone: /tmp/repo\n"
        "agent_backend: cursor\n",
        encoding="utf-8",
    )
    overlay = tmp_path / "engineering-work-loop.yaml"
    overlay.write_text("github_user: alice\n", encoding="utf-8")

    monkeypatch.setattr(
        "engineering_work_loop_config.toolkit_example_path",
        lambda root=None: example,
    )
    cfg = load_config(overlay)
    assert cfg["github_user"] == "alice"
    # Default concrete loop is implement-loop → status paths derive from that stem.
    assert cfg["status"]["latest_md"].endswith("implement-loop-latest.md")


def test_render_launchd_plist_claude_backend():
    prev = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "tok-123"
    try:
        plist = render_launchd_plist(toolkit_root(), {"agent_backend": "claude"})
        assert "CLAUDE_CODE_OAUTH_TOKEN" in plist
        assert "tok-123" in plist
        assert "COPILOT_ALLOW_ALL" not in plist
    finally:
        if prev is None:
            os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
        else:
            os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = prev


def test_resolve_repo_clones(tmp_path):
    repo_with = tmp_path / "withclone"
    (repo_with / ".git").mkdir(parents=True)
    primary = tmp_path / "primary"
    (primary / ".git").mkdir(parents=True)
    cfg = {
        "repos": [
            {"owner": "o", "repo": "a", "clone_path": str(repo_with)},
            {"owner": "o", "repo": "b"},
            {"owner": "o", "repo": "c", "clone_path": str(tmp_path / "missing")},
        ],
        "git": {"primary_clone": str(primary)},
    }
    rows = resolve_repo_clones(cfg)
    assert rows[0] == ("o", "a", str(repo_with), True)
    assert rows[1] == ("o", "b", str(primary), True)  # fallback exists
    assert rows[2][3] is False  # missing clone


def test_render_launchd_plist_optional_api_key():
    prev = os.environ.get("CURSOR_API_KEY")
    os.environ["CURSOR_API_KEY"] = "test-key"
    try:
        plist = render_launchd_plist(toolkit_root(), {"agent_backend": "cursor"})
        assert "CURSOR_API_KEY" in plist
        assert "test-key" in plist
    finally:
        if prev is None:
            os.environ.pop("CURSOR_API_KEY", None)
        else:
            os.environ["CURSOR_API_KEY"] = prev


# --- multi-instance support (v2) ---

import engineering_work_loop_setup as _setup_mod  # noqa: E402
import engineering_work_loop_config as _cfg_mod  # noqa: E402


def test_default_loop_is_implement_loop(monkeypatch):
    # The family default concrete loop is implement-loop (engineering-work-loop is
    # the family umbrella, not a concrete loop). Bare install → implement-loop.
    monkeypatch.delenv("ENGINEERING_LOOP_INSTANCE", raising=False)
    monkeypatch.delenv("ENGINEERING_LOOP_NAME", raising=False)
    assert _setup_mod.launchd_label() == "com.ai-sdlc.implement-loop"
    assert _cfg_mod.operator_overlay_path().name == "implement-loop.yaml"
    assert _setup_mod.windows_task_name() == "ai-sdlc-implement-loop"


def test_spec_loop_identifiers(monkeypatch):
    monkeypatch.delenv("ENGINEERING_LOOP_INSTANCE", raising=False)
    monkeypatch.setenv("ENGINEERING_LOOP_NAME", "spec-loop")
    assert _setup_mod.launchd_label() == "com.ai-sdlc.spec-loop"
    assert _cfg_mod.operator_overlay_path().name == "spec-loop.yaml"
    assert _setup_mod.windows_task_name() == "ai-sdlc-spec-loop"


def test_loops_have_separate_logs(monkeypatch):
    # Family members must not clobber each other's logs. cron_log + the config
    # state/status defaults all derive from the loop name.
    monkeypatch.delenv("ENGINEERING_LOOP_INSTANCE", raising=False)
    monkeypatch.setenv("ENGINEERING_LOOP_NAME", "implement-loop")
    impl_cron = _setup_mod.cron_log().name
    impl_state = _cfg_mod.load_config(_cfg_mod.toolkit_example_path())["state_log"]
    monkeypatch.setenv("ENGINEERING_LOOP_NAME", "spec-loop")
    spec_cron = _setup_mod.cron_log().name
    spec_state = _cfg_mod.load_config(_cfg_mod.toolkit_example_path())["state_log"]
    assert impl_cron == "implement-loop-cron.log"
    assert spec_cron == "spec-loop-cron.log"
    assert impl_state.endswith("implement-loop.log")
    assert spec_state.endswith("spec-loop.log")
    assert impl_state != spec_state


def test_named_instance_suffixes_all_identifiers(monkeypatch):
    monkeypatch.setenv("ENGINEERING_LOOP_INSTANCE", "v2")
    monkeypatch.delenv("ENGINEERING_LOOP_NAME", raising=False)  # default implement-loop
    assert _setup_mod.launchd_label() == "com.ai-sdlc-v2.implement-loop"
    assert _setup_mod.launchd_plist().name == "com.ai-sdlc-v2.implement-loop.plist"
    assert _cfg_mod.operator_overlay_path().name == "implement-loop-v2.yaml"
    assert _setup_mod.latest_md().name == "implement-loop-latest-v2.md"
    assert _setup_mod.windows_task_name() == "ai-sdlc-v2-implement-loop"
    # worktree root and reports dir are suffixed too (no collision with the default)
    dirs = [d.name for d in _setup_mod.local_state_dirs()]
    assert "worktrees-v2" in dirs
    assert "implement-loop-reports-v2" in dirs


def test_plist_injects_base_ref_instance_and_loop(monkeypatch):
    from engineering_work_loop_config import toolkit_root
    monkeypatch.setenv("ENGINEERING_LOOP_INSTANCE", "v2")
    monkeypatch.setenv("ENGINEERING_LOOP_NAME", "spec-loop")
    plist = _setup_mod.render_launchd_plist(
        toolkit_root(),
        {"agent_backend": "claude", "git": {"base_ref": "origin/phase2"}},
    )
    assert "com.ai-sdlc-v2.spec-loop" in plist
    assert "ENGINEERING_LOOP_INSTANCE" in plist and ">v2<" in plist
    assert "ENGINEERING_LOOP_NAME" in plist and ">spec-loop<" in plist
    assert "ENGINEERING_LOOP_PROMPT" in plist and "spec-loop.prompt.md" in plist
    assert "ENGINEERING_LOOP_BASE_REF" in plist and "origin/phase2" in plist


def test_plist_omits_base_ref_when_unset(monkeypatch):
    from engineering_work_loop_config import toolkit_root
    monkeypatch.delenv("ENGINEERING_LOOP_INSTANCE", raising=False)
    monkeypatch.delenv("ENGINEERING_LOOP_BASE_REF", raising=False)
    plist = _setup_mod.render_launchd_plist(toolkit_root(), {"agent_backend": "cursor"})
    assert "ENGINEERING_LOOP_BASE_REF" not in plist
