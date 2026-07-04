"""Tests for set_project_status.py — mechanical-only, gate-protected Status moves."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import set_project_status as sps  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "set_project_status.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def test_gate_status_rejected_by_cli():
    # A human-gate status must never be settable by automation.
    for gate in ("Ready for Dev", "Approved", "Ready for Spec"):
        r = _run("--org", "o", "--project", "1", "--content-url", "u", "--status", gate)
        assert r.returncode == 2
        assert "human gate" in r.stderr.lower() or "mechanical" in r.stderr.lower()


def test_mechanical_statuses_are_allowed_set():
    assert sps.MECHANICAL_STATUSES == {"Backlog", "In Progress", "In review", "Done"}


def test_gate_statuses_are_protected_set():
    assert sps.GATE_STATUSES == {"Ready for Spec", "Approved", "Ready for Dev"}


def _patch(monkeypatch, *, item_id="ITEM", current=None, options=None):
    options = options or {
        "Backlog": "b",
        "In review": "r",
        "Done": "d",
        "Ready for Spec": "rs",
        "Ready for Dev": "rd",
    }
    monkeypatch.setattr(sps, "resolve_project", lambda org, num: ("PROJ", "FIELD", options))
    monkeypatch.setattr(sps, "find_item", lambda pid, url: (item_id, current))
    calls = []
    monkeypatch.setattr(sps, "set_status", lambda *a: calls.append(a))
    return calls


def _main(monkeypatch, status, current, *extra_flags, **kw):
    calls = _patch(monkeypatch, current=current, **kw)
    argv = ["x", "--org", "o", "--project", "1", "--content-url", "https://x/1", "--status", status]
    argv.extend(extra_flags)
    monkeypatch.setattr(sys, "argv", argv)
    rc = sps.main()
    return rc, calls


def test_sets_in_review_when_current_backlog(monkeypatch):
    rc, calls = _main(monkeypatch, "In review", "Backlog")
    assert rc == 0 and len(calls) == 1  # status was set


def test_noop_when_current_is_human_gate(monkeypatch):
    # The item is in Ready for Dev — a Done event must NOT overwrite the gate.
    rc, calls = _main(monkeypatch, "Done", "Ready for Dev")
    assert rc == 0 and calls == []  # gate protected, no write


def test_noop_when_not_on_board(monkeypatch):
    rc, calls = _main(monkeypatch, "Done", None, item_id=None)
    assert rc == 0 and calls == []


def test_noop_when_already_target(monkeypatch):
    rc, calls = _main(monkeypatch, "Done", "Done")
    assert rc == 0 and calls == []


def test_sets_done_from_in_review(monkeypatch):
    rc, calls = _main(monkeypatch, "Done", "In review")
    assert rc == 0 and len(calls) == 1


def test_done_override_finalizes_from_gate(monkeypatch):
    # A merge with --allow-gate-override finalizes even a gated card to Done.
    rc, calls = _main(monkeypatch, "Done", "Ready for Dev", "--allow-gate-override")
    assert rc == 0 and len(calls) == 1


# --- spec-merge promotion (Ready for Spec -> Ready for Dev) ---

def test_spec_promote_moves_ready_for_spec_to_ready_for_dev(monkeypatch):
    rc, calls = _main(monkeypatch, "Ready for Dev", "Ready for Spec", "--spec-merge-promote")
    assert rc == 0 and len(calls) == 1  # the one authorized gate-to-gate move


def test_spec_promote_rejected_without_flag():
    # Ready for Dev is a gate; without --spec-merge-promote the CLI refuses it outright.
    r = _run("--org", "o", "--project", "1", "--content-url", "u", "--status", "Ready for Dev")
    assert r.returncode == 2


def test_spec_promote_only_from_ready_for_spec(monkeypatch):
    # The flag must NOT let a card jump to Ready for Dev from some other gate (e.g. Approved).
    rc, calls = _main(monkeypatch, "Ready for Dev", "Approved", "--spec-merge-promote")
    assert rc == 0 and calls == []  # left untouched — only Ready-for-Spec promotes


# --- dev-review move (Ready for Dev -> In review) ---

def test_dev_review_moves_ready_for_dev_to_in_review(monkeypatch):
    # A code PR became ready -> work started -> In review, past the Ready-for-Dev gate.
    rc, calls = _main(monkeypatch, "In review", "Ready for Dev", "--allow-dev-review")
    assert rc == 0 and len(calls) == 1


def test_dev_review_noop_without_flag(monkeypatch):
    # Without --allow-dev-review, In review must NOT overwrite the Ready-for-Dev gate.
    rc, calls = _main(monkeypatch, "In review", "Ready for Dev")
    assert rc == 0 and calls == []  # gate protected


def test_dev_review_flag_only_affects_ready_for_dev(monkeypatch):
    # The flag must not let In review overwrite a DIFFERENT gate (e.g. Ready for Spec).
    rc, calls = _main(monkeypatch, "In review", "Ready for Spec", "--allow-dev-review")
    assert rc == 0 and calls == []


def test_spec_promote_flag_cannot_set_other_gate():
    # The flag only unlocks target == Ready for Dev; Approved stays refused at the CLI.
    r = _run("--org", "o", "--project", "1", "--content-url", "u",
             "--status", "Approved", "--spec-merge-promote")
    assert r.returncode == 2
