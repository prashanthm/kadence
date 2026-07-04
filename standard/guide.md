# The AI-SDLC: How It Works (v2)

## The core idea

A lean, AI-native SDLC in **three product layers** with an **autonomous delivery loop**.
Humans decide *what* and *whether*; agents draft the detail and implement; the loop ships
draft PRs; humans merge. Status, dates, and progress live in GitHub — markdown holds only
durable intent.

## The lifecycle at a glance

```
Initiative (why, funding)                         initiatives/<slug>/initiative.md
  └─ Product Brief (what; Epic Index = order)     initiatives/<slug>/product-brief.md
       └─ Epic (a capability area)                initiatives/<slug>/epics/<slug>.md   → GitHub Epic issue + milestone
            └─ Feature (THE build unit; What/Why/AC)  initiatives/<slug>/features/<slug>.md → GitHub Feature issue
                 └─ [human moves it to "Ready for Dev"]  ← the one gate
                      └─ the loop implements it in a worktree, verifies Loop AC,
                         opens a DRAFT PR with a spec folder in the code repo
                              specs/<feature-slug>/{spec,plan,tasks}.md
                         → human reviews, marks ready, merges → board → Done
```

## How each stage works

- **Initiative / Brief / Epic (product, human-led).** The Product Owner states why the
  program exists and the Epic Index (release order by phase name — no dates). Agents draft
  the epics; each becomes a GitHub Epic issue on a milestone/phase.
- **Feature (the contract).** A feature carries What / Why / Acceptance Criteria and a
  `Depends On`. It is the build unit: **one feature → one PR → `Closes #`**. No status, no
  positional ID, no issue number in the file — the issue links back by slug + branch.
- **Ready for Dev (the gate).** A human reviews the feature and moves its card to
  `Ready for Dev`. Nothing is built before this.
- **Build (the loop).** The engineering-work-loop picks up `Ready for Dev` issues, works
  each in an isolated git worktree, authors the code-repo **spec folder**
  (`specs/<feature>/{spec,plan,tasks}.md`), implements, and **re-runs every Loop AC
  `verify:` itself** (the agent's `[x]` is advisory). It opens a **draft** PR with a Work
  Fix Report (gated by `report_gate.py`: a real `Skill used` + diff-vs-claim).
- **Sizing happens at generation.** `feature-generation` reasons about scope and emits each
  feature as one coherent, PR-sized increment (a big capability becomes several features with a
  `Depends On` graph). There is no separate decompose step and no file/line-count tripwire —
  Loop AC verifies behavior, not diff size.
- **Review & merge (human).** The operator marks the draft ready; a reviewer approves; a
  human merges. The board advances to `Done` via the merged PR's `Closes #`.

## Gates: where humans say yes or no

- **`Ready for Dev`** — the product/engineering handoff. The only gate before the loop runs.
- **PR review + merge** — the loop never merges (unless risk-based auto-land is explicitly
  enabled, default OFF). The reviewable artifact is the diff.

## The enforcement principle

**The agent proposes; the deterministic harness disposes.** Every reward — a green Loop AC,
"done", a board moving to Done — is backed by a command the harness re-runs (`verify_loop_ac
--enforce`) and an artifact it can see (`report_gate` diff-vs-claim). Never an agent's
self-report. `ai-sdlc doctor` gates every change to the toolkit itself.

## Where things live (durable vs mutable)

- **Durable (markdown, forever):** initiative · product brief · epics · features · ADRs ·
  `specs/<feature>/`. Slug-named; no status, dates, or IDs.
- **Mutable (GitHub, live):** status (issue/board) · dates & progress (Projects Roadmap +
  milestones) · what shipped (releases/tags).
- **The join:** slug + branch + `Closes owner/repo#N`; the issue links out to the doc + spec.

## Getting started

1. Draft an initiative + product brief (Epic Index = release order).
2. Generate epics → features (What/Why/AC; slug-named).
3. Move a feature to `Ready for Dev`.
4. Run the loop (`engineering-work-loop`) — it opens a draft PR.
5. Review, merge. The board tracks itself.

See [glossary.md](glossary.md) for the locked vocabulary and [project-board.md](project-board.md)
for the status automation.
