---
name: release-notes-generation
description: Generate release notes from merged PRs and epic descriptions for PO review. Use at release-notes stage.
---

# Release Notes Generation Skill

## Purpose

Produce changelog-style release notes linking PRs to features and epics for stakeholder review.

## When to Use

- Orchestrator `release-notes` stage
- Before production ship

## Required Inputs

- Merged PRs in release scope
- Epic and feature descriptions
- Template: [`templates/release-notes.md`](../../templates/release-notes.md)

## Required Workflow

1. Collect merged PRs with task/feature links.
2. Group by epic or user-visible capability.
3. Summarize changes, breaking changes, migration notes.
4. Write to `initiatives/<slug>/release-notes-<phase>.md` or a repo CHANGELOG section.
5. Request PO review before publishing.

## Multi-Agent Delegation

| Field | Value |
|-------|-------|
| Stage | `release-notes` |
| Activity type | AuthorReleaseNotes |

## Verification

- [ ] Every in-scope PR represented
- [ ] Breaking changes called out
- [ ] PO review requested — not published without approval
