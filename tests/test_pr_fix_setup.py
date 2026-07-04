"""Tests for pr_fix_setup — agent auth verification."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))



# --- claude backend accepts stored login (no env token) ---

def test_claude_auth_accepts_stored_login(monkeypatch, tmp_path):
    import pr_fix_setup as s
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # `claude auth status` reports logged in
    class R:
        returncode = 0
        stdout = "Logged in as you@example.com"
        stderr = ""
    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: R())
    s.verify_agent_auth("claude", "claude")  # must not raise


def test_claude_auth_accepts_stored_claude_json(monkeypatch, tmp_path):
    import pr_fix_setup as s
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # auth status fails, but ~/.claude.json has oauthAccount
    class R:
        returncode = 1
        stdout = ""
        stderr = "not a tty"
    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: R())
    fake_home = tmp_path
    (fake_home / ".claude.json").write_text('{"oauthAccount": {"email": "x"}}')
    monkeypatch.setattr(s.Path, "home", staticmethod(lambda: fake_home))
    s.verify_agent_auth("claude", "claude")  # must not raise


def test_claude_auth_fails_when_no_login(monkeypatch, tmp_path):
    import pr_fix_setup as s
    import pytest
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    class R:
        returncode = 1
        stdout = ""
        stderr = "not logged in"
    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: R())
    monkeypatch.setattr(s.Path, "home", staticmethod(lambda: tmp_path))  # no .claude.json
    with pytest.raises(RuntimeError, match="auth not found"):
        s.verify_agent_auth("claude", "claude")
