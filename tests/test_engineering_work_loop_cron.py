"""Tests for engineering_work_loop_cron.fire() sequential multi-item loop."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import engineering_work_loop_cron as cron  # noqa: E402

# Capture pristine module functions so each test restores them (the shim runs all
# tests in one process; pytest fixtures would isolate, our shim does not).
_ORIG = {
    "discover": cron.discover,
    "run_agent": cron.run_agent,
    "run_agent_with_fallback": cron.run_agent_with_fallback,
    "write_firing_report": cron.write_firing_report,
    "ensure_dirs": cron.ensure_dirs,
    "load_config": cron.load_config,
    "append_state_log_entry": cron.append_state_log_entry,
}


def _restore():
    for name, fn in _ORIG.items():
        setattr(cron, name, fn)


def _patch(monkeypatch_like, candidates, run_agent_impl):
    """Patch cron module-level deps for an isolated fire() run."""
    # (v2) No execute_auto_compliance — every candidate goes straight to the agent.
    cron.discover = lambda cfg, *, force_issue=None, dry_run=False: {
        "candidates": candidates,
        "skipped_count": 1,
        "pool_size": len(candidates) + 1,
    }

    def fallback_adapter(sd, cp, *, force_issue=None, clone_path=None, base_ref=None):
        code, out = run_agent_impl(
            sd, cp, force_issue=force_issue, clone_path=clone_path, base_ref=base_ref
        )
        return code, out, "claude"

    cron.run_agent_with_fallback = fallback_adapter
    cron.write_firing_report = lambda cfg, rep: None
    cron.ensure_dirs = lambda cfg: None
    cron.load_config = lambda p: {"status": {}}
    cron.append_state_log_entry = lambda cfg, **kw: None  # no real file I/O in tests


def _candidates():
    return [
        {
            "kind": "issue",
            "owner": "o",
            "repo": "r",
            "number": 1,
            "clone_path": "/p/r",
            "base_ref": "origin/phase2",
        },
        {
            "kind": "issue",
            "owner": "o",
            "repo": "r",
            "number": 2,
            "clone_path": "/p/r",
            "base_ref": "origin/phase2",
        },
        {"kind": "dependabot_pr", "owner": "o", "repo": "r2", "number": 9, "clone_path": "/p/r2"},
    ]


def test_fire_iterates_all_candidates():
    calls = []

    def fake_run_agent(sd, cp, *, force_issue=None, clone_path=None, base_ref=None):
        calls.append((force_issue, clone_path, base_ref))
        return (0, f"ran {force_issue}")

    _patch(None, _candidates(), fake_run_agent)
    rep = cron.fire(Path("scripts"), "/tmp/cfg.yaml")

    assert rep["outcome"] == "agent_complete"
    assert rep["processed_count"] == 3
    assert rep["skipped_count"] == 1
    # dependabot gets force_issue=None; issues get their number + base_ref; each its clone_path
    assert calls == [
        (1, "/p/r", "origin/phase2"),
        (2, "/p/r", "origin/phase2"),
        (None, "/p/r2", None),
    ]


def test_fire_error_isolation():
    def fake_run_agent(sd, cp, *, force_issue=None, clone_path=None, base_ref=None):
        if force_issue == 2:
            raise RuntimeError("boom")
        return (0, "ok")

    _patch(None, _candidates(), fake_run_agent)
    rep = cron.fire(Path("scripts"), "/tmp/cfg.yaml")

    # all three attempted; item 2 recorded as error; overall agent_error
    assert rep["processed_count"] == 3
    assert rep["outcome"] == "agent_error"
    by_num = {it["candidate"]["number"]: it["outcome"] for it in rep["items"]}
    assert by_num[1] == "agent_complete"
    assert by_num[2] == "agent_error"
    assert by_num[9] == "agent_complete"


def _fallback_calls(monkeypatch, configured_backend, succeed_on):
    """Run run_agent_with_fallback with a stubbed run_agent + configured backend,
    returning the ordered list of backends attempted."""
    _restore()
    calls = []

    def fake_run_agent(sd, cp, *, force_issue=None, clone_path=None, base_ref=None, backend=None):
        calls.append(backend)
        return (0, "ok") if backend == succeed_on else (1, f"{backend} failed")

    # control the configured backend the fallback reads from config
    import engineering_work_loop_config as ewc
    monkeypatch.setattr(
        ewc, "load_config", lambda *_a, **_k: {"agent_backend": configured_backend}
    )
    orig = cron.run_agent
    cron.run_agent = fake_run_agent
    try:
        code, out, used = cron.run_agent_with_fallback(
            Path("scripts"), "/tmp/cfg", force_issue=1, clone_path="/p/r"
        )
    finally:
        cron.run_agent = orig
    return calls, code, used


def test_configured_backend_leads_the_chain(monkeypatch):
    # Claude is the only backend; it is tried first and succeeds.
    calls, code, used = _fallback_calls(monkeypatch, "claude", succeed_on="claude")
    assert calls[0] == "claude"
    assert code == 0 and used == "claude"


def test_claude_only_chain_when_backend_fails(monkeypatch):
    # Claude is the only backend, so a failing firing has nothing to fall through to:
    # the chain is exactly ["claude"] and the loop reports that failure.
    calls, code, used = _fallback_calls(monkeypatch, "claude", succeed_on="none")
    assert calls == ["claude"]
    assert code != 0 and used == "claude"


def test_default_chain_when_no_configured_backend(monkeypatch):
    # empty/unknown configured backend -> the default (claude-only) chain is used.
    calls, code, used = _fallback_calls(monkeypatch, "", succeed_on="claude")
    assert calls == ["claude"]
    assert code == 0 and used == "claude"


def test_fire_no_work():
    _patch(None, [], lambda *a, **k: (0, ""))
    # no_work uses the legacy build_report path; override counts present in report
    rep = cron.fire(Path("scripts"), "/tmp/cfg.yaml")
    assert rep["outcome"] == "no_work"


def test_fire_dry_run_lists_all_without_agent():
    called = {"n": 0}

    def fake_run_agent(*a, **k):
        called["n"] += 1
        return (0, "")

    _patch(None, _candidates(), fake_run_agent)
    rep = cron.fire(Path("scripts"), "/tmp/cfg.yaml", dry_run=True)

    assert called["n"] == 0
    assert rep["outcome"] == "dry_run"
    assert len(rep["items"]) == 3


def test_fire_writes_state_log_per_issue():
    recorded = []
    _patch(None, _candidates(), lambda sd, cp, *, force_issue=None, clone_path=None, base_ref=None: (0, "ok"))
    cron.append_state_log_entry = lambda cfg, **kw: recorded.append(
        (kw["owner"], kw["repo"], kw["number"], kw["outcome"]))
    try:
        cron.fire(Path("scripts"), "/tmp/cfg.yaml")
    finally:
        _restore()
    # only the two issue candidates get cooldown entries; dependabot (#9) does not
    assert [(o, r, n) for (o, r, n, _oc) in recorded] == [("o", "r", 1), ("o", "r", 2)]
    assert all(oc == "agent_complete" for *_x, oc in recorded)


def test_fire_dry_run_does_not_write_state_log():
    recorded = []
    _patch(None, _candidates(), lambda *a, **k: (0, ""))
    cron.append_state_log_entry = lambda cfg, **kw: recorded.append(kw)
    try:
        cron.fire(Path("scripts"), "/tmp/cfg.yaml", dry_run=True)
    finally:
        _restore()
    assert recorded == []  # dry run must not mutate cooldown state


def test_run_agent_command_uses_git_bash_on_windows():
    _restore()
    cron.is_windows = lambda: True
    cron.resolve_bash = lambda: r"C:\Git\bin\bash.exe"
    try:
        cmd = cron.run_agent_command(Path("s"))
    finally:
        _restore()
    assert cmd == [r"C:\Git\bin\bash.exe", str(Path("s") / "engineering-work-loop.sh")]


def test_firing_lock_is_mutually_exclusive(tmp_path, monkeypatch):
    # A second firing_lock() while the first is held must NOT acquire — this is what
    # prevents a manual force-fire from colliding with the scheduled cron.
    monkeypatch.setattr(cron, "_lock_path", lambda: tmp_path / "loop.lock")
    with cron.firing_lock() as a1:
        assert a1 is True
        with cron.firing_lock() as a2:
            assert a2 is False  # already held → busy
    # released → re-acquire succeeds
    with cron.firing_lock() as a3:
        assert a3 is True
