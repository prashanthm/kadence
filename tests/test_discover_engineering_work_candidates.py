"""Tests for discover_engineering_work_candidates.py"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from classify_work_item import classify_issue  # noqa: E402
from discover_engineering_work_candidates import (  # noqa: E402
    base_ref_for_repo,
    cap_candidates_per_repo,
    clone_path_for_repo,
    cooldown_active,
    discover,
    discover_dependabot_prs,
    discovery_cfg,
    fetch_project_status_map,
    parse_priority_value,
    priority_score,
    project_cfg,
    repo_project_cfg,
    read_state_log,
    skip_reason,
    status_gate_skip_reason,
)


def test_discovery_cfg_defaults():
    cfg = load_config_from_example()
    d = discovery_cfg(cfg)
    assert d["require_loop_ac_on_issue"] is False
    # (v2) synthesize_missing_loop_ac / writeback_loop_ac removed — no synthesis path.


def load_config_from_example():
    from engineering_work_loop_config import load_config
    from engineering_work_loop_config import toolkit_example_path

    return load_config(toolkit_example_path())


def test_skip_deferred_label():
    # A skip-label on an OPEN issue must cause discovery to skip it. (The label-skip
    # mechanism is generic; kept in v2 for loop-deferred/loop-blocked handling.)
    issue = {
        "number": 244,
        "title": "chore: something",
        "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
        "labels": [{"name": "loop-blocked"}],
    }
    classification = classify_issue(issue["title"], issue["body"], ["chore", "loop-blocked"])
    cfg = load_config_from_example()
    reason = skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: [])
    assert reason == "deferred_label"


def test_skip_deferred_label_mixed_case():
    issue = {
        "number": 244,
        "title": "chore: x",
        "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
        "labels": [{"name": "Loop-Blocked"}],
    }
    classification = classify_issue(issue["title"], issue["body"], ["chore", "Loop-Blocked"])
    cfg = load_config_from_example()
    assert skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: []) == "deferred_label"


def test_skip_reason_unassigned_issue():
    # `gh issue list --assignee @me` already scopes discovery, but skip_reason
    # must independently re-verify assignment — a stray/misconfigured gh auth
    # context must never let an unassigned issue through (regression for PR #71
    # on edi-artifact-registry-infra#44, opened for an issue assigned to no one).
    issue = {
        "number": 44,
        "title": "chore: x",
        "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
        "labels": [{"name": "chore"}],
        "assignees": [],
    }
    classification = classify_issue(issue["title"], issue["body"], ["chore"])
    cfg = load_config_from_example()
    cfg["github_user"] = "prashanthm"
    cfg["enabled_work_types"] = ["chore"]
    assert skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: []) == "not_assigned_to_operator"


def test_skip_reason_assigned_to_someone_else():
    issue = {
        "number": 44,
        "title": "chore: x",
        "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
        "labels": [{"name": "chore"}],
        "assignees": [{"login": "someone-else"}],
    }
    classification = classify_issue(issue["title"], issue["body"], ["chore"])
    cfg = load_config_from_example()
    cfg["github_user"] = "prashanthm"
    cfg["enabled_work_types"] = ["chore"]
    assert skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: []) == "not_assigned_to_operator"


def test_skip_reason_assigned_to_operator_passes():
    issue = {
        "number": 44,
        "title": "chore: x",
        "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
        "labels": [{"name": "chore"}],
        "assignees": [{"login": "someone-else"}, {"login": "prashanthm"}],
    }
    classification = classify_issue(issue["title"], issue["body"], ["chore"])
    cfg = load_config_from_example()
    cfg["github_user"] = "prashanthm"
    cfg["enabled_work_types"] = ["chore"]
    assert skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: []) is None


def test_skip_reason_no_github_user_configured_skips_check():
    # No github_user in config -> the assignee re-check can't run (nothing to
    # compare against) — falls through to the rest of the gates rather than
    # blocking everything. Existing behavior for configs that omit github_user.
    issue = {
        "number": 44,
        "title": "chore: x",
        "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
        "labels": [{"name": "chore"}],
        "assignees": [],
    }
    classification = classify_issue(issue["title"], issue["body"], ["chore"])
    cfg = load_config_from_example()
    cfg["github_user"] = ""
    cfg["enabled_work_types"] = ["chore"]
    assert skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: []) is None


def test_skip_reason_cooldown_from_state():
    # An item with a fresh state_log entry must be skipped on the next firing
    # (regression for the dead-cooldown bug that re-picked #241 every firing).
    issue = {
        "number": 241,
        "title": "chore: x",
        "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
        "labels": [{"name": "chore"}],
        "assignees": [{"login": "prashanthm"}],
    }
    classification = classify_issue(issue["title"], issue["body"], ["chore"])
    cfg = load_config_from_example()
    cfg["enabled_work_types"] = ["chore"]
    state = {"o/r#241": {"fired_at": "2099-01-01T00:00:00+00:00"}}
    reason = skip_reason(issue, classification, cfg, "o", "r", state, lambda a: [])
    assert reason == "cooldown"


def test_append_state_log_round_trip(tmp_path):
    from engineering_work_loop_status import append_state_log_entry
    from discover_engineering_work_candidates import cooldown_active

    log = tmp_path / "state.log"
    cfg = {"state_log": str(log)}
    append_state_log_entry(cfg, owner="your-org", repo="product-workspace",
                           number=241, outcome="agent_complete")
    state = read_state_log(str(log))
    key = "your-org/product-workspace#241"
    assert key in state
    assert cooldown_active(key, state, 24) is True


def test_skip_human_only():
    # A task with no verifiable Loop AC defaults to human-only tier → skipped.
    issue = {
        "number": 1,
        "title": "e01-f01-t01 — risky change",
        "body": "**Work item type:** task\n**Risk tier:** human-only\n",
        "labels": [{"name": "task"}],
        "assignees": [{"login": "prashanthm"}],
    }
    classification = classify_issue(issue["title"], issue["body"], ["task"])
    cfg = load_config_from_example()
    reason = skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: [])
    assert reason == "human_only"


def test_skip_assist_without_flag():
    issue = {
        "number": 1,
        "title": "fix: something",
        "body": "**Work item type:** fix\n**Risk tier:** assist\n",
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "prashanthm"}],
    }
    classification = {"work_item_type": "fix", "risk_tier": "assist"}
    cfg = load_config_from_example()
    cfg["process_assist"] = False
    reason = skip_reason(issue, classification, cfg, "o", "r", {}, lambda a: [])
    assert reason == "assist_disabled"


# (v2) test_priority_score_p0_compliance_first removed — no compliance band.


def test_cooldown_active_recent():
    key = "o/r#1"
    state = {key: {"fired_at": "2099-01-01T00:00:00+00:00"}}
    assert cooldown_active(key, state, 24) is True


def test_parse_priority_value():
    assert parse_priority_value("**Priority:** P1") == 1


# --- clone_path resolution ---

def test_clone_path_for_repo_uses_entry():
    cfg = {
        "repos": [{"owner": "o", "repo": "r", "clone_path": "/p/r"}],
        "git": {"primary_clone": "/p/primary"},
    }
    assert clone_path_for_repo(cfg, "o", "r") == "/p/r"


def test_clone_path_for_repo_falls_back_to_primary():
    cfg = {
        "repos": [{"owner": "o", "repo": "r"}],
        "git": {"primary_clone": "/p/primary"},
    }
    assert clone_path_for_repo(cfg, "o", "r") == "/p/primary"
    # unknown repo also falls back
    assert clone_path_for_repo(cfg, "x", "y") == "/p/primary"


# --- base_ref resolution ---

def test_base_ref_for_repo_uses_entry():
    cfg = {
        "repos": [{"owner": "o", "repo": "r", "base_ref": "origin/phase2"}],
        "git": {"base_ref": "origin/main"},
    }
    assert base_ref_for_repo(cfg, "o", "r") == "origin/phase2"


def test_base_ref_for_repo_falls_back_to_top_level_then_default():
    cfg = {"repos": [{"owner": "o", "repo": "r"}], "git": {"base_ref": "origin/develop"}}
    assert base_ref_for_repo(cfg, "o", "r") == "origin/develop"
    cfg_no_git = {"repos": [{"owner": "o", "repo": "r"}]}
    assert base_ref_for_repo(cfg_no_git, "o", "r") == "origin/main"
    # unknown repo also falls back
    assert base_ref_for_repo({"repos": []}, "x", "y") == "origin/main"


def test_clone_path_rejects_traversal():
    import pytest

    cfg = {
        "repos": [{"owner": "o", "repo": "r", "clone_path": "/p/../../etc"}],
        "git": {"primary_clone": "/p/primary"},
    }
    with pytest.raises(ValueError):
        clone_path_for_repo(cfg, "o", "r")


# --- per-repo cap ---

def test_cap_candidates_per_repo():
    pool = [{"owner": "o", "repo": "b", "number": i} for i in range(8)]
    capped = cap_candidates_per_repo(pool, 5)
    assert len(capped) == 5
    assert [c["number"] for c in capped] == [0, 1, 2, 3, 4]


def test_cap_candidates_per_repo_independent_groups():
    pool = (
        [{"owner": "o", "repo": "a", "number": i} for i in range(6)]
        + [{"owner": "o", "repo": "b", "number": 100 + i} for i in range(6)]
    )
    capped = cap_candidates_per_repo(pool, 5)
    assert len(capped) == 10
    a = [c for c in capped if c["repo"] == "a"]
    b = [c for c in capped if c["repo"] == "b"]
    assert len(a) == 5 and len(b) == 5


def _fake_gh_factory(issues_per_repo, recorder=None):
    def fake_gh(args):
        if recorder is not None:
            recorder.append(args)
        if args[0] == "issue" and args[1] == "list":
            full = args[args.index("--repo") + 1]
            n = issues_per_repo.get(full, 0)
            return [
                {
                    "number": i,
                    "title": f"chore: x{i}",
                    "body": "## Loop AC\n- [ ] AC-1: x\n  - verify: `grep x`",
                    "labels": [{"name": "chore"}],
                }
                for i in range(1, n + 1)
            ]
        if args[0] == "pr" and args[1] == "list":
            return []
        return []

    return fake_gh


def _multi_repo_cfg():
    return {
        "repos": [
            {"owner": "your-org", "repo": "pw", "clone_path": "/p/pw"},
            {"owner": "your-org", "repo": "er", "clone_path": "/p/er"},
        ],
        "git": {"primary_clone": "/p/pw"},
        "enabled_work_types": ["chore", "dependabot"],
        "max_items_per_repo": 5,
        "state_log": "/tmp/does-not-exist.log",
        "cooldown_hours": 24,
        "process_assist": False,
        "discovery": {
            "require_loop_ac_on_issue": False,
        },
    }


def test_discover_caps_per_repo_and_counts_skipped():
    cfg = _multi_repo_cfg()
    fake = _fake_gh_factory({"your-org/pw": 6, "your-org/er": 0})
    res = discover(cfg, gh_run=fake)
    assert res["pool_size"] == 6
    assert len(res["candidates"]) == 5
    assert res["skipped_count"] == 1
    assert res["candidate"] == res["candidates"][0]
    assert all(c["clone_path"] == "/p/pw" for c in res["candidates"])


def test_discover_multi_repo_groups_independently():
    cfg = _multi_repo_cfg()
    fake = _fake_gh_factory({"your-org/pw": 6, "your-org/er": 6})
    res = discover(cfg, gh_run=fake)
    assert len(res["candidates"]) == 10
    clones = {(c["owner"], c["repo"]): c["clone_path"] for c in res["candidates"]}
    assert clones[("your-org", "pw")] == "/p/pw"
    assert clones[("your-org", "er")] == "/p/er"


def test_discover_honors_legacy_global_ceiling():
    cfg = _multi_repo_cfg()
    cfg["max_items_per_firing"] = 2
    fake = _fake_gh_factory({"your-org/pw": 6, "your-org/er": 6})
    res = discover(cfg, gh_run=fake)
    assert len(res["candidates"]) == 2


def test_dependabot_uses_app_filter():
    cfg = _multi_repo_cfg()
    recorder = []
    fake = _fake_gh_factory({}, recorder=recorder)
    discover_dependabot_prs(cfg, fake)
    pr_calls = [a for a in recorder if a[:2] == ["pr", "list"]]
    assert pr_calls, "no pr list call recorded"
    for call in pr_calls:
        assert "--app" in call
        assert call[call.index("--app") + 1] == "dependabot"
        assert "--author" not in call


# --- Project-board Status gating ---

def test_project_cfg_defaults_off():
    assert project_cfg({}) == {"org": None, "number": None, "status_gates": []}


def test_project_cfg_parsed():
    p = project_cfg({"project": {"org": "your-org", "number": 19,
                                 "status_gates": ["Ready for Dev"]}})
    assert p == {"org": "your-org", "number": 19, "status_gates": ["Ready for Dev"]}


def test_project_cfg_scalar_gate_coerced_to_list():
    p = project_cfg({"project": {"status_gates": "Ready for Dev"}})
    assert p["status_gates"] == ["Ready for Dev"]


def test_status_gate_off_when_no_gates():
    # No gates configured → never skips on Status (backward compatible).
    issue = {"url": "https://github.com/o/r/issues/1"}
    assert status_gate_skip_reason(issue, {}, []) is None


def test_status_gate_allows_matching_status():
    issue = {"url": "https://github.com/o/r/issues/1"}
    smap = {"https://github.com/o/r/issues/1": "Ready for Dev"}
    assert status_gate_skip_reason(issue, smap, ["Ready for Dev"]) is None


def test_status_gate_skips_wrong_status():
    issue = {"url": "https://github.com/o/r/issues/1"}
    smap = {"https://github.com/o/r/issues/1": "Backlog"}
    assert status_gate_skip_reason(issue, smap, ["Ready for Dev"]) == "project_status_gated"


def test_status_gate_skips_issue_not_on_board():
    # Fails closed: an issue absent from the project map is skipped.
    issue = {"url": "https://github.com/o/r/issues/99"}
    assert status_gate_skip_reason(issue, {}, ["Ready for Dev"]) == "project_status_gated"


def test_fetch_project_status_map_parses_graphql():
    page = {
        "data": {"organization": {"projectV2": {"items": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {"content": {"url": "https://github.com/o/r/issues/1"},
                 "fieldValues": {"nodes": [
                     {"name": "Ready for Dev", "field": {"name": "Status"}}]}},
                {"content": {"url": "https://github.com/o/r/issues/2"},
                 "fieldValues": {"nodes": [
                     {"name": "Backlog", "field": {"name": "Status"}}]}},
            ],
        }}}}
    }
    calls = []

    def fake_gh(args):
        calls.append(args)
        return page

    out = fetch_project_status_map("your-org", 19, fake_gh)
    assert out == {
        "https://github.com/o/r/issues/1": "Ready for Dev",
        "https://github.com/o/r/issues/2": "Backlog",
    }
    assert calls and calls[0][0] == "api" and calls[0][1] == "graphql"


def test_fetch_project_status_map_fails_open_to_empty_on_error():
    def boom(args):
        raise RuntimeError("project api down")

    assert fetch_project_status_map("your-org", 19, boom) == {}


def test_project_cfg_empty_number_yaml_quirk():
    # YAML `number:` with no value parses to {} — must coerce to None, not crash.
    assert project_cfg({"project": {"number": {}}})["number"] is None
    assert project_cfg({"project": {"number": ""}})["number"] is None
    assert project_cfg({"project": {"number": "19"}})["number"] == 19


def test_repo_project_cfg_uses_repo_entry_override():
    cfg = {"project": {"org": "your-org", "number": 19, "status_gates": ["Ready for Dev"]}}
    entry = {"owner": "your-org", "repo": "subsurface-agentic-ai",
             "project": {"org": "your-org", "number": 22, "status_gates": ["Ready for Dev"]}}
    p = repo_project_cfg(entry, cfg)
    assert p["number"] == 22  # repo override, not the top-level 19


def test_repo_project_cfg_falls_back_to_top_level():
    cfg = {"project": {"org": "your-org", "number": 19, "status_gates": ["Ready for Dev"]}}
    entry = {"owner": "your-org", "repo": "product-workspace"}  # no project block
    p = repo_project_cfg(entry, cfg)
    assert p["number"] == 19


def test_repo_project_cfg_repo_can_disable_gating():
    # A repo with an explicit empty project block is NOT gated even if top-level gates.
    cfg = {"project": {"org": "your-org", "number": 19, "status_gates": ["Ready for Dev"]}}
    entry = {"owner": "your-org", "repo": "engineering-reports", "project": {}}
    p = repo_project_cfg(entry, cfg)
    assert p["status_gates"] == [] and p["number"] is None
